#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RAW_SUFFIX = "_raw.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a reviewed transcript draft from a raw local OpenAI Whisper transcript."
    )
    parser.add_argument("raw_transcript", help="Path to input/transcripts/raw/<basename>_raw.md")
    parser.add_argument(
        "--apply-safe-cleanup",
        action="store_true",
        help="Conservatively remove only obvious technical repetitions from intro/outro.",
    )
    return parser.parse_args()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def basename_from_raw(raw_path: Path) -> str:
    name = raw_path.name
    if not name.endswith(RAW_SUFFIX):
        raise ValueError(f"Raw transcript filename must end with {RAW_SUFFIX}: {raw_path}")
    return name[: -len(RAW_SUFFIX)]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def split_markdown(markdown: str) -> tuple[dict[str, str], str]:
    if not markdown.startswith("---\n"):
        return {}, markdown

    end = markdown.find("\n---", 4)
    if end == -1:
        return {}, markdown

    raw_frontmatter = markdown[4:end].strip()
    body = markdown[end + len("\n---") :].lstrip("\n")
    frontmatter: dict[str, str] = {}
    for line in raw_frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip()
    return frontmatter, body


def strip_raw_heading(body: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].strip() == "# Trascrizione grezza":
        lines = lines[1:]
        if lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value).replace("\n", " ").strip()


def reviewed_markdown(
    *,
    transcript_text: str,
    source_raw: str,
    source_report: str,
    review_status: str,
    safe_original: Any,
    safe_cleanup_applied: bool,
    quality_warnings_count: int,
    normalization_candidates_count: int,
) -> str:
    frontmatter = {
        "source_type": "reviewed_transcript",
        "source_raw_transcript": source_raw,
        "source_transcription_report": source_report,
        "review_status": review_status,
        "safe_for_analysis_original": safe_original,
        "safe_cleanup_applied": safe_cleanup_applied,
        "quality_warnings_count": quality_warnings_count,
        "normalization_candidates_count": normalization_candidates_count,
        "status": "reviewed_draft",
    }
    frontmatter_text = "\n".join(f"{key}: {yaml_scalar(value)}" for key, value in frontmatter.items())
    return f"---\n{frontmatter_text}\n---\n\n# Trascrizione revisionata\n\n{transcript_text.strip()}\n"


def sentence_pattern(phrase: str) -> str:
    phrase = phrase.strip()
    if not phrase:
        return ""
    escaped = re.escape(phrase)
    escaped = escaped.replace(r"\ ", r"\s+")
    return escaped


def first_sentence(evidence: str) -> str:
    match = re.match(r"\s*([^.!?\n]+[.!?])", evidence)
    if match:
        return match.group(1).strip()
    return evidence.strip()


def remove_intro_loop(text: str, warning: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    phrase = first_sentence(str(warning.get("evidence", "")))
    pattern = sentence_pattern(phrase)
    if not pattern:
        return text, None

    match = re.match(rf"^((?:{pattern}\s*){{4,}})", text, flags=re.IGNORECASE)
    if not match:
        return text, None

    repeated_block = match.group(1)
    occurrences = len(re.findall(pattern, repeated_block, flags=re.IGNORECASE))
    if occurrences <= 3:
        return text, None

    cleaned = phrase + " " + text[match.end() :].lstrip()
    return cleaned, {
        "type": "intro_loop_removed",
        "evidence": phrase,
        "occurrences_removed": occurrences - 1,
        "reason": "Repeated phrase detected in transcription quality warnings.",
    }


def remove_outro_repetition(text: str, warning: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    evidence = str(warning.get("evidence", "")).strip()
    if not evidence:
        return text, None

    units = re.findall(r"[^.!?\n]+[.!?]?", evidence)
    normalized_units = [unit.strip() for unit in units if unit.strip()]
    if len(normalized_units) < 2:
        return text, None

    phrase = normalized_units[0]
    if any(unit.lower().strip(" .!?") != phrase.lower().strip(" .!?") for unit in normalized_units):
        return text, None

    pattern = sentence_pattern(phrase)
    match = re.search(rf"((?:{pattern}\s*){{2,}})$", text.strip(), flags=re.IGNORECASE)
    if not match:
        return text, None

    repeated_block = match.group(1)
    occurrences = len(re.findall(pattern, repeated_block, flags=re.IGNORECASE))
    if occurrences <= 1:
        return text, None

    cleaned = text.strip()[: match.start(1)].rstrip() + "\n\n" + phrase
    return cleaned.strip(), {
        "type": "outro_repetition_removed",
        "evidence": phrase,
        "occurrences_removed": occurrences - 1,
        "reason": "Repeated phrase detected in transcription quality warnings.",
    }


def warning_is_blocking(warning: dict[str, Any]) -> bool:
    if warning.get("severity") == "high":
        return True
    return warning.get("type") in {"possible_intro_loop"} and warning.get("severity") == "warning"


def apply_safe_cleanup(
    text: str,
    quality_warnings: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    cleaned = text
    removed: list[dict[str, Any]] = []
    resolved_warning_ids: set[int] = set()

    for idx, warning in enumerate(quality_warnings):
        warning_type = warning.get("type")
        if warning_type == "possible_intro_loop" or (
            warning_type == "repeated_phrase" and warning.get("start") in (None, 0, 0.0)
        ):
            new_text, removal = remove_intro_loop(cleaned, warning)
            if removal:
                cleaned = new_text
                removed.append(removal)
                resolved_warning_ids.add(idx)

    for idx, warning in enumerate(quality_warnings):
        if warning.get("type") == "possible_outro_repetition":
            new_text, removal = remove_outro_repetition(cleaned, warning)
            if removal:
                cleaned = new_text
                removed.append(removal)
                resolved_warning_ids.add(idx)

    remaining = [warning for idx, warning in enumerate(quality_warnings) if idx not in resolved_warning_ids]
    return cleaned, removed, remaining


def manual_review_items(
    *,
    quality_warnings: list[dict[str, Any]],
    remaining_warnings: list[dict[str, Any]],
    normalization_candidates: list[dict[str, Any]],
    cleanup_requested: bool,
    removed_repetitions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    unresolved = remaining_warnings if cleanup_requested else quality_warnings
    for warning in unresolved:
        if warning_is_blocking(warning) or warning.get("severity") in {"warning", "high"}:
            items.append(
                {
                    "type": "quality_warning",
                    "source": "transcription_report",
                    "severity": warning.get("severity", "warning"),
                    "message": warning.get("message", "Review transcription quality warning."),
                    "evidence": warning.get("evidence", ""),
                    "action": "manual_review_required",
                }
            )

    for candidate in normalization_candidates:
        items.append(
            {
                "type": "normalization_candidate",
                "source": "transcription_report",
                "observed": candidate.get("observed"),
                "possible_canonical": candidate.get("possible_canonical"),
                "action": "candidate_only_do_not_auto_replace",
            }
        )

    if cleanup_requested and not removed_repetitions and quality_warnings:
        items.append(
            {
                "type": "safe_cleanup_not_applied",
                "source": "review_step",
                "message": "No technical repetition was removed because warnings were not safe enough for automatic cleanup.",
                "action": "manual_review_required",
            }
        )

    return items


def review_status_for(
    *,
    safe_original: Any,
    cleanup_requested: bool,
    remaining_warnings: list[dict[str, Any]],
) -> str:
    if safe_original is True and not cleanup_requested:
        return "ready_for_analysis"
    if cleanup_requested and not any(warning_is_blocking(warning) for warning in remaining_warnings):
        return "ready_for_analysis"
    return "needs_manual_review"


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    raw_path = Path(args.raw_transcript).expanduser()
    if not raw_path.is_absolute():
        raw_path = root / raw_path
    raw_path = raw_path.resolve()

    try:
        base_name = basename_from_raw(raw_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    report_path = root / "output" / "transcription" / f"{base_name}_transcription.json"
    reviewed_path = root / "input" / "transcripts" / "reviewed" / f"{base_name}_reviewed.md"
    review_report_path = root / "output" / "review" / f"{base_name}_review.json"

    if not raw_path.exists():
        print(f"Raw transcript not found: {rel(raw_path, root)}", file=sys.stderr)
        return 1
    if not report_path.exists():
        print(f"Transcription report not found: {rel(report_path, root)}", file=sys.stderr)
        return 1

    report = load_json(report_path)
    markdown = raw_path.read_text(encoding="utf-8")
    _, body = split_markdown(markdown)
    transcript_text = strip_raw_heading(body)

    quality_warnings = [
        warning for warning in report.get("quality_warnings", []) if isinstance(warning, dict)
    ]
    normalization_candidates = [
        candidate for candidate in report.get("normalization_candidates", []) if isinstance(candidate, dict)
    ]

    removed_repetitions: list[dict[str, Any]] = []
    remaining_warnings = quality_warnings
    reviewed_text = transcript_text

    if args.apply_safe_cleanup:
        reviewed_text, removed_repetitions, remaining_warnings = apply_safe_cleanup(
            transcript_text,
            quality_warnings,
        )

    safe_original = report.get("safe_for_analysis")
    review_status = review_status_for(
        safe_original=safe_original,
        cleanup_requested=args.apply_safe_cleanup,
        remaining_warnings=remaining_warnings,
    )

    reviewed_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed_path.write_text(
        reviewed_markdown(
            transcript_text=reviewed_text,
            source_raw=rel(raw_path, root),
            source_report=rel(report_path, root),
            review_status=review_status,
            safe_original=safe_original,
            safe_cleanup_applied=args.apply_safe_cleanup and bool(removed_repetitions),
            quality_warnings_count=len(quality_warnings),
            normalization_candidates_count=len(normalization_candidates),
        ),
        encoding="utf-8",
    )

    items = manual_review_items(
        quality_warnings=quality_warnings,
        remaining_warnings=remaining_warnings,
        normalization_candidates=normalization_candidates,
        cleanup_requested=args.apply_safe_cleanup,
        removed_repetitions=removed_repetitions,
    )
    review_payload = {
        "status": "ok",
        "source_raw_transcript": rel(raw_path, root),
        "source_transcription_report": rel(report_path, root),
        "output_reviewed_transcript": rel(reviewed_path, root),
        "safe_for_analysis_original": safe_original,
        "review_status": review_status,
        "safe_cleanup_applied": args.apply_safe_cleanup and bool(removed_repetitions),
        "removed_repetitions": removed_repetitions,
        "manual_review_items": items,
        "normalization_candidates": normalization_candidates,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "message": "Reviewed transcript prepared. Raw transcript was not modified.",
    }
    write_json(review_report_path, review_payload)

    print(f"Reviewed transcript: {rel(reviewed_path, root)}")
    print(f"Review report: {rel(review_report_path, root)}")
    print(f"Review status: {review_status}")
    if removed_repetitions:
        print(f"Removed repetitions: {len(removed_repetitions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
