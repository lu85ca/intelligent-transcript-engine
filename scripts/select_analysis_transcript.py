#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


RAW_SUFFIX = "_raw.md"
REVIEWED_SUFFIX = "_reviewed.md"
NORMALIZED_SUFFIX = "_normalized.md"

MSG_REQUIRES_REVIEW = "Transcript requires review before agent-driven analysis."
MSG_MISSING_TRANSCRIPT = "No transcript found for the requested basename."
MSG_UNSAFE_OVERRIDE = "Unsafe raw transcript selected only because --allow-unsafe-raw was provided."

REASON_NORMALIZED = "Normalized transcript exists and has priority over reviewed/raw."
REASON_REVIEWED = "Reviewed transcript exists and has priority over raw."
REASON_RAW_SAFE = "Only raw transcript exists and technical report marks it as safe for analysis."
REASON_RAW_UNSAFE = "Only raw transcript exists and technical report marks it as not safe for analysis."
REASON_RAW_UNKNOWN = "Only raw transcript exists and safe_for_analysis is not available."
REASON_REPORT_MISSING = "Only raw transcript exists but the technical transcription report is missing."
REASON_REPORT_INVALID = "Only raw transcript exists but the technical transcription report is not readable."
REASON_MISSING = "No normalized, reviewed or raw transcript exists for the requested basename."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select the transcript that should be used for agent-driven analysis."
    )
    parser.add_argument(
        "transcript",
        help="Transcript basename or path under input/transcripts/raw, reviewed or normalized.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full technical selection decision.")
    parser.add_argument("--verbose", action="store_true", help="Print checked paths to stderr.")
    parser.add_argument(
        "--allow-unsafe-raw",
        action="store_true",
        help="Manual/debug override: select raw even when safe_for_analysis is false, null or unavailable.",
    )
    return parser.parse_args()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def strip_known_suffix(name: str) -> str:
    for suffix in (NORMALIZED_SUFFIX, REVIEWED_SUFFIX, RAW_SUFFIX):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    if name.endswith(".md"):
        return name[:-3]
    return name


def basename_from_input(value: str, root: Path) -> str:
    path = Path(value).expanduser()
    if path.suffix == ".md" or "/" in value:
        if not path.is_absolute():
            path = root / path
        return strip_known_suffix(path.name)
    return strip_known_suffix(value)


def transcript_paths(root: Path, basename: str) -> dict[str, Path]:
    return {
        "normalized": root / "input" / "transcripts" / "normalized" / f"{basename}{NORMALIZED_SUFFIX}",
        "reviewed": root / "input" / "transcripts" / "reviewed" / f"{basename}{REVIEWED_SUFFIX}",
        "raw": root / "input" / "transcripts" / "raw" / f"{basename}{RAW_SUFFIX}",
        "technical_report": root / "output" / "transcription" / f"{basename}_transcription.json",
    }


def checked_paths(paths: dict[str, Path], root: Path) -> dict[str, str]:
    return {key: rel(path, root) for key, path in paths.items()}


def load_technical_report(report_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not report_path.exists():
        return None, "missing"
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "invalid"
    if not isinstance(data, dict):
        return None, "invalid"
    return data, None


def report_safe_for_analysis(report: dict[str, Any] | None) -> bool | None:
    if report is None:
        return None
    value = report.get("safe_for_analysis")
    return value if isinstance(value, bool) else None


def base_decision(
    *,
    basename: str,
    paths: dict[str, Path],
    root: Path,
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "basename": basename,
        "selected_transcript": None,
        "selected_level": None,
        "decision": None,
        "safe_for_analysis": report_safe_for_analysis(report),
        "requires_review": False,
        "reason": None,
        "checked_paths": checked_paths(paths, root),
    }


def attach_report_metadata(payload: dict[str, Any], report: dict[str, Any] | None) -> None:
    if report is None:
        payload["quality_warnings"] = []
        payload["normalization_candidates"] = []
        return
    payload["quality_warnings"] = report.get("quality_warnings", [])
    payload["normalization_candidates"] = report.get("normalization_candidates", [])


def select_transcript(
    *,
    input_value: str,
    root: Path,
    allow_unsafe_raw: bool = False,
) -> tuple[dict[str, Any], int]:
    basename = basename_from_input(input_value, root)
    paths = transcript_paths(root, basename)
    report, report_error = load_technical_report(paths["technical_report"])
    payload = base_decision(basename=basename, paths=paths, root=root, report=report)

    if paths["normalized"].exists():
        payload.update(
            {
                "selected_transcript": rel(paths["normalized"], root),
                "selected_level": "normalized",
                "decision": "selected_normalized",
                "requires_review": False,
                "reason": REASON_NORMALIZED,
            }
        )
        return payload, 0

    if paths["reviewed"].exists():
        payload.update(
            {
                "selected_transcript": rel(paths["reviewed"], root),
                "selected_level": "reviewed",
                "decision": "selected_reviewed",
                "requires_review": False,
                "reason": REASON_REVIEWED,
            }
        )
        return payload, 0

    if paths["raw"].exists():
        safe_for_analysis = report_safe_for_analysis(report)
        attach_report_metadata(payload, report)

        if safe_for_analysis is True:
            payload.update(
                {
                    "selected_transcript": rel(paths["raw"], root),
                    "selected_level": "raw",
                    "decision": "selected_raw_safe",
                    "requires_review": False,
                    "reason": REASON_RAW_SAFE,
                }
            )
            return payload, 0

        if allow_unsafe_raw:
            reason = MSG_UNSAFE_OVERRIDE
            if report_error == "missing":
                reason = f"{reason} {REASON_REPORT_MISSING}"
            elif report_error == "invalid":
                reason = f"{reason} {REASON_REPORT_INVALID}"
            elif safe_for_analysis is False:
                reason = f"{reason} {REASON_RAW_UNSAFE}"
            else:
                reason = f"{reason} {REASON_RAW_UNKNOWN}"
            payload.update(
                {
                    "selected_transcript": rel(paths["raw"], root),
                    "selected_level": "raw",
                    "decision": "selected_raw_unsafe_override",
                    "requires_review": False,
                    "reason": reason,
                    "unsafe_override": True,
                }
            )
            return payload, 0

        if report_error == "missing":
            reason = REASON_REPORT_MISSING
        elif report_error == "invalid":
            reason = REASON_REPORT_INVALID
        elif safe_for_analysis is False:
            reason = REASON_RAW_UNSAFE
        else:
            reason = REASON_RAW_UNKNOWN
        payload.update(
            {
                "decision": "requires_review",
                "requires_review": True,
                "reason": reason,
            }
        )
        return payload, 1

    payload.update(
        {
            "decision": "missing_transcript",
            "requires_review": True,
            "reason": REASON_MISSING,
        }
    )
    return payload, 1


def print_verbose(payload: dict[str, Any]) -> None:
    print("Checked transcript paths:", file=sys.stderr)
    for key, path in payload["checked_paths"].items():
        print(f"- {key}: {path}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    root = project_root()
    payload, code = select_transcript(
        input_value=args.transcript,
        root=root,
        allow_unsafe_raw=args.allow_unsafe_raw,
    )

    if args.verbose:
        print_verbose(payload)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif payload["selected_transcript"]:
        print(payload["selected_transcript"])
    else:
        print(f"{MSG_REQUIRES_REVIEW} {payload['reason'] or MSG_MISSING_TRANSCRIPT}", file=sys.stderr)

    return code


if __name__ == "__main__":
    raise SystemExit(main())
