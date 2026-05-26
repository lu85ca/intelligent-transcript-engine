#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REVIEWED_SUFFIX = "_reviewed.md"
NORMALIZED_SUFFIX = "_normalized.md"
ALLOWED_CONTEXTS = {
    "work_meetings": "knowledge/work_meetings",
    "macro_categories/finance": "knowledge/macro_categories/finance",
    "macro_categories/travel": "knowledge/macro_categories/travel",
    "macro_categories/social_media_management": "knowledge/macro_categories/social_media_management",
    "macro_categories/generic": "knowledge/macro_categories/generic",
}

MSG_OUTPUT_EXISTS = "Normalized transcript and report already exist. Re-run with --force to overwrite."
MSG_DRY_RUN = "Dry run: no files were written."


@dataclass(frozen=True)
class Rule:
    id: str
    observed: tuple[str, ...]
    canonical: str
    match: str
    case_sensitive: bool
    enabled: bool
    source: str
    notes: str | None = None


@dataclass(frozen=True)
class Candidate:
    rule: Rule
    observed: str
    pattern: re.Pattern[str]
    priority: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a reviewed transcript using approved normalization rules."
    )
    parser.add_argument(
        "basename",
        help="Transcript basename or path to input/transcripts/reviewed/<basename>_reviewed.md.",
    )
    parser.add_argument(
        "--context",
        default="work_meetings",
        choices=sorted(ALLOWED_CONTEXTS),
        help="Knowledge context to use. Default: work_meetings.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Print replacements without writing files.")
    parser.add_argument("--verbose", action="store_true", help="Print diagnostic details.")
    return parser.parse_args()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_bool(value: str, default: bool) -> bool:
    if value == "":
        return default
    lowered = strip_quotes(value).lower()
    if lowered in {"true", "yes", "1"}:
        return True
    if lowered in {"false", "no", "0"}:
        return False
    return default


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "[]":
        return []
    if value == "":
        return ""
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    return strip_quotes(value)


def parse_minimal_yaml_rules(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    rules_start: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == "rules: []":
            return []
        if line.strip() == "rules:":
            rules_start = idx + 1
            break
    if rules_start is None:
        return []

    rules: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    active_list_key: str | None = None

    for raw_line in lines[rules_start:]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()

        if indent == 0:
            break

        if indent == 2 and stripped.startswith("- "):
            if current is not None:
                rules.append(current)
            current = {}
            active_list_key = None
            remainder = stripped[2:].strip()
            if remainder:
                key, value = split_key_value(remainder)
                current[key] = parse_scalar(value)
            continue

        if current is None:
            continue

        if indent == 4 and ":" in stripped:
            key, value = split_key_value(stripped)
            if value == "":
                current[key] = []
                active_list_key = key
            else:
                current[key] = parse_scalar(value)
                active_list_key = None
            continue

        if indent >= 6 and stripped.startswith("- ") and active_list_key:
            current.setdefault(active_list_key, [])
            if isinstance(current[active_list_key], list):
                current[active_list_key].append(strip_quotes(stripped[2:].strip()))

    if current is not None:
        rules.append(current)
    return rules


def split_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        return text.strip(), ""
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def normalize_rule(raw_rule: dict[str, Any], source: Path, skipped: list[dict[str, Any]]) -> Rule | None:
    rule_id = str(raw_rule.get("id", "")).strip()
    observed = raw_rule.get("observed")
    canonical = str(raw_rule.get("canonical", "")).strip()
    match = str(raw_rule.get("match", "word")).strip() or "word"

    if not rule_id or not isinstance(observed, list) or not observed or not canonical:
        skipped.append(
            {
                "rule_id": rule_id or "non rilevato",
                "source": source.as_posix(),
                "reason": "Rule is missing required id, observed list, or canonical value.",
            }
        )
        return None

    if match not in {"word", "phrase", "regex"}:
        skipped.append(
            {
                "rule_id": rule_id,
                "source": source.as_posix(),
                "reason": f"Unsupported match type: {match}",
            }
        )
        return None

    enabled = parse_bool(str(raw_rule.get("enabled", "true")), default=True)
    case_sensitive = parse_bool(str(raw_rule.get("case_sensitive", "false")), default=False)
    notes = raw_rule.get("notes")
    return Rule(
        id=rule_id,
        observed=tuple(str(item) for item in observed if str(item).strip()),
        canonical=canonical,
        match=match,
        case_sensitive=case_sensitive,
        enabled=enabled,
        source=source.as_posix(),
        notes=str(notes) if notes else None,
    )


def load_rules(root: Path, context: str) -> tuple[list[Rule], list[str], list[dict[str, Any]]]:
    source_paths = [
        root / "knowledge" / "global" / "normalization_rules.yml",
        root / ALLOWED_CONTEXTS[context] / "normalization_rules.yml",
    ]
    skipped: list[dict[str, Any]] = []
    rules: list[Rule] = []
    for source in source_paths:
        for raw_rule in parse_minimal_yaml_rules(source):
            rule = normalize_rule(raw_rule, source, skipped)
            if rule:
                rules.append(rule)
    return rules, [rel(path, root) for path in source_paths if path.exists()], skipped


def basename_from_input(value: str, root: Path) -> tuple[str, Path]:
    path = Path(value).expanduser()
    if path.suffix == ".md" or "/" in value:
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        if not path.name.endswith(REVIEWED_SUFFIX):
            raise ValueError(f"Reviewed transcript filename must end with {REVIEWED_SUFFIX}: {path}")
        return path.name[: -len(REVIEWED_SUFFIX)], path

    basename = value.removesuffix(REVIEWED_SUFFIX).removesuffix(NORMALIZED_SUFFIX)
    return basename, root / "input" / "transcripts" / "reviewed" / f"{basename}{REVIEWED_SUFFIX}"


def split_markdown(markdown: str) -> tuple[str, str]:
    if not markdown.startswith("---\n"):
        return "", markdown
    end = markdown.find("\n---", 4)
    if end == -1:
        return "", markdown
    return markdown[: end + len("\n---")], markdown[end + len("\n---") :].lstrip("\n")


def strip_reviewed_heading(body: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].strip() == "# Trascrizione revisionata":
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


def normalized_markdown(
    *,
    body: str,
    source_transcript: str,
    context: str,
    normalization_applied: bool,
    report_path: str,
) -> str:
    frontmatter = {
        "source_type": "normalized_transcript",
        "status": "normalized_transcript",
        "source_transcript": source_transcript,
        "normalization_context": context,
        "normalization_applied": normalization_applied,
        "normalization_report": report_path,
    }
    frontmatter_text = "\n".join(f"{key}: {yaml_scalar(value)}" for key, value in frontmatter.items())
    return f"---\n{frontmatter_text}\n---\n\n# Trascrizione normalizzata\n\n{body.strip()}\n"


def find_conflicts(rules: list[Rule]) -> tuple[set[str], list[dict[str, Any]]]:
    observed_map: dict[tuple[str, bool], dict[str, set[str]]] = {}
    for rule in rules:
        if not rule.enabled:
            continue
        for observed in rule.observed:
            key = (observed if rule.case_sensitive else observed.lower(), rule.case_sensitive)
            observed_map.setdefault(key, {}).setdefault(rule.canonical, set()).add(rule.id)

    conflict_rule_ids: set[str] = set()
    conflicts: list[dict[str, Any]] = []
    for (observed, case_sensitive), canonical_map in observed_map.items():
        if len(canonical_map) <= 1:
            continue
        rule_ids = sorted({rid for ids in canonical_map.values() for rid in ids})
        conflict_rule_ids.update(rule_ids)
        conflicts.append(
            {
                "observed": observed,
                "case_sensitive": case_sensitive,
                "canonical_values": sorted(canonical_map),
                "rule_ids": rule_ids,
                "action": "ambiguous_rules_skipped",
            }
        )
    return conflict_rule_ids, conflicts


def compile_candidate(rule: Rule, observed: str) -> Candidate:
    flags = 0 if rule.case_sensitive else re.IGNORECASE
    if rule.match == "word":
        pattern = re.compile(rf"(?<!\w){re.escape(observed)}(?!\w)", flags)
        priority = 1
    elif rule.match == "phrase":
        pattern = re.compile(re.escape(observed), flags)
        priority = 0
    else:
        pattern = re.compile(observed, flags)
        priority = 2
    return Candidate(rule=rule, observed=observed, pattern=pattern, priority=priority)


def build_candidates(rules: list[Rule], conflict_rule_ids: set[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    for rule in rules:
        if not rule.enabled or rule.id in conflict_rule_ids:
            continue
        for observed in rule.observed:
            candidates.append(compile_candidate(rule, observed))
    return sorted(candidates, key=lambda item: (item.priority, -len(item.observed), item.rule.id, item.observed))


def ranges_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def apply_rules(body: str, candidates: list[Candidate]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    replacements: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    skipped_overlaps: list[dict[str, Any]] = []

    for candidate in candidates:
        for match in candidate.pattern.finditer(body):
            span = match.span()
            if span[0] == span[1]:
                continue
            if any(ranges_overlap(span, existing) for existing in occupied):
                skipped_overlaps.append(
                    {
                        "rule_id": candidate.rule.id,
                        "observed": candidate.observed,
                        "canonical": candidate.rule.canonical,
                        "match": candidate.rule.match,
                        "reason": "Match overlapped with a higher-priority replacement.",
                    }
                )
                continue
            occupied.append(span)
            replacements.append(
                {
                    "start": span[0],
                    "end": span[1],
                    "rule_id": candidate.rule.id,
                    "observed": match.group(0),
                    "configured_observed": candidate.observed,
                    "canonical": candidate.rule.canonical,
                    "match": candidate.rule.match,
                }
            )

    replacements.sort(key=lambda item: item["start"])
    chunks: list[str] = []
    last = 0
    for replacement in replacements:
        chunks.append(body[last : replacement["start"]])
        chunks.append(replacement["canonical"])
        last = replacement["end"]
    chunks.append(body[last:])
    normalized = "".join(chunks)
    return normalized, summarize_replacements(replacements), skipped_overlaps


def summarize_replacements(replacements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: dict[tuple[str, str, str, str], int] = {}
    for replacement in replacements:
        key = (
            replacement["rule_id"],
            replacement["configured_observed"],
            replacement["canonical"],
            replacement["match"],
        )
        summary[key] = summary.get(key, 0) + 1
    return [
        {
            "rule_id": rule_id,
            "observed": observed,
            "canonical": canonical,
            "count": count,
            "match": match,
        }
        for (rule_id, observed, canonical, match), count in sorted(summary.items())
    ]


def report_payload(
    *,
    basename: str,
    source_transcript: str,
    normalized_transcript: str,
    context: str,
    knowledge_sources: list[str],
    rules_loaded: int,
    rules_enabled: int,
    replacements: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    skipped_rules: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "basename": basename,
        "source_transcript": source_transcript,
        "normalized_transcript": normalized_transcript,
        "normalization_context": context,
        "knowledge_sources": knowledge_sources,
        "normalization_performed": bool(replacements),
        "rules_loaded": rules_loaded,
        "rules_enabled": rules_enabled,
        "rules_applied": len({item["rule_id"] for item in replacements}),
        "total_replacements": sum(int(item["count"]) for item in replacements),
        "replacements": replacements,
        "conflicts": conflicts,
        "skipped_rules": skipped_rules,
        "warnings": warnings,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message": "Normalization completed using approved rules only.",
    }


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]

    try:
        basename, reviewed_path = basename_from_input(args.basename, root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    normalized_path = root / "input" / "transcripts" / "normalized" / f"{basename}{NORMALIZED_SUFFIX}"
    report_path = root / "output" / "normalization" / f"{basename}_normalization.json"

    if not reviewed_path.exists():
        print(f"Reviewed transcript not found: {rel(reviewed_path, root)}", file=sys.stderr)
        return 1

    if not args.force and not args.dry_run and (normalized_path.exists() or report_path.exists()):
        print(MSG_OUTPUT_EXISTS)
        print(f"Normalized transcript: {rel(normalized_path, root)}")
        print(f"Normalization report: {rel(report_path, root)}")
        return 0

    rules, knowledge_sources, skipped_rules = load_rules(root, args.context)
    conflict_rule_ids, conflicts = find_conflicts(rules)
    if conflicts:
        skipped_rules.extend(
            {
                "rule_id": rule_id,
                "reason": "Rule skipped because its observed value conflicts with another canonical value.",
            }
            for rule_id in sorted(conflict_rule_ids)
        )
    candidates = build_candidates(rules, conflict_rule_ids)

    markdown = reviewed_path.read_text(encoding="utf-8")
    _, body = split_markdown(markdown)
    transcript_body = strip_reviewed_heading(body)
    normalized_body, replacements, overlap_warnings = apply_rules(transcript_body, candidates)
    warnings = overlap_warnings

    source_transcript = rel(reviewed_path, root)
    normalized_transcript = rel(normalized_path, root)
    report = report_payload(
        basename=basename,
        source_transcript=source_transcript,
        normalized_transcript=normalized_transcript,
        context=args.context,
        knowledge_sources=knowledge_sources,
        rules_loaded=len(rules),
        rules_enabled=len([rule for rule in rules if rule.enabled]),
        replacements=replacements,
        conflicts=conflicts,
        skipped_rules=skipped_rules,
        warnings=warnings,
    )

    if args.dry_run:
        print(MSG_DRY_RUN)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(
        normalized_markdown(
            body=normalized_body,
            source_transcript=source_transcript,
            context=args.context,
            normalization_applied=bool(replacements),
            report_path=rel(report_path, root),
        ),
        encoding="utf-8",
    )
    write_json(report_path, report)

    if args.verbose:
        print(f"Rules loaded: {len(rules)}")
        print(f"Rules enabled: {len([rule for rule in rules if rule.enabled])}")
        print(f"Total replacements: {report['total_replacements']}")
    print(f"Normalized transcript: {normalized_transcript}")
    print(f"Normalization report: {rel(report_path, root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
