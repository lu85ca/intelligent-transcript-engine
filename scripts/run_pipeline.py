#!/usr/bin/env python3
"""Local rule-based transcript pipeline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

OUTPUT_JSON_DIR = Path("output/json")
OUTPUT_MARKDOWN_DIR = Path("output/markdown")
NOT_DETECTED = "non rilevato"

CLASSIFICATION_RULES = {
    "meeting": [
        "decisione",
        "azioni",
        "task",
        "scadenza",
        "owner",
        "riunione",
        "prossimi passi",
        "facciamo",
        "dobbiamo",
    ],
    "webinar": [
        "webinar",
        "domande",
        "partecipanti",
        "slide",
        "presentazione",
        "sessione",
        "q&a",
    ],
    "youtube_video": [
        "iscriviti",
        "like",
        "canale",
        "video",
        "commenti",
        "descrizione",
        "oggi parliamo",
    ],
}

RECIPE_BY_TYPE = {
    "generic": "recipes/generic.md",
    "meeting": "recipes/meeting.md",
    "webinar": "recipes/webinar.md",
    "youtube_video": "recipes/youtube_video.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the transcript intelligence pipeline."
    )
    parser.add_argument(
        "transcript",
        help="Path to the transcript file to analyze.",
    )
    return parser.parse_args()


def read_transcript(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Transcript file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Transcript path is not a file: {path}")

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Transcript file is empty: {path}")

    return text


def classify_transcript(text: str) -> dict:
    normalized_text = text.lower()
    matches = {}

    for content_type, keywords in CLASSIFICATION_RULES.items():
        matched_keywords = [
            keyword for keyword in keywords if keyword.lower() in normalized_text
        ]
        matches[content_type] = matched_keywords

    ranked = sorted(
        matches.items(),
        key=lambda item: (len(item[1]), item[0]),
        reverse=True,
    )
    best_type, best_signals = ranked[0]
    secondary_type, secondary_signals = ranked[1]

    if len(best_signals) < 2:
        content_type = "generic"
        confidence = 0.4 if best_signals else 0.25
        signals = best_signals
        secondary = best_type if best_signals else NOT_DETECTED
        reason = (
            "Segnali insufficienti per una classificazione specialistica; "
            "uso della recipe generic."
        )
    else:
        content_type = best_type
        confidence = min(0.95, 0.55 + (len(best_signals) * 0.1))
        signals = best_signals
        secondary = secondary_type if secondary_signals else NOT_DETECTED
        reason = (
            "Classificazione basata sui segnali testuali rilevati: "
            f"{', '.join(best_signals)}."
        )

    return {
        "type": content_type,
        "confidence": round(confidence, 2),
        "secondary_type": secondary,
        "signals": signals,
        "reason": reason,
        "recommended_recipe": RECIPE_BY_TYPE[content_type],
    }


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" -\t")


def _content_lines(text: str) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue
        if set(line) <= {"#", "-", "*", "_"}:
            continue
        lines.append(line)
    return lines


def _first_markdown_heading(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            return title or NOT_DETECTED
    return NOT_DETECTED


def _matching_lines(lines: list[str], keywords: list[str]) -> list[str]:
    matches = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            matches.append(line)
    return matches or [NOT_DETECTED]


def _action_items(lines: list[str]) -> list[dict]:
    action_lines = _matching_lines(
        lines,
        ["azione", "azioni", "task", "owner", "scadenza", "prossimi passi", "dobbiamo"],
    )
    if action_lines == [NOT_DETECTED]:
        return [
            {
                "description": NOT_DETECTED,
                "owner": NOT_DETECTED,
                "due_date": NOT_DETECTED,
            }
        ]

    return [
        {
            "description": line,
            "owner": NOT_DETECTED,
            "due_date": NOT_DETECTED,
        }
        for line in action_lines
    ]


def build_generic_analysis(text: str, classification: dict) -> dict:
    lines = _content_lines(text)
    title = _first_markdown_heading(lines)
    body_lines = [line for line in lines if not line.startswith("#")]
    summary = body_lines[0] if body_lines else NOT_DETECTED
    key_points = body_lines[:5] if body_lines else [NOT_DETECTED]

    return {
        "title": title,
        "content_type": classification["type"],
        "summary": summary,
        "key_points": key_points,
        "facts": key_points,
        "interpretations": [NOT_DETECTED],
        "decisions": _matching_lines(body_lines, ["decisione", "deciso", "decidiamo"]),
        "action_items": _action_items(body_lines),
        "open_questions": [
            line for line in body_lines if line.endswith("?")
        ]
        or _matching_lines(body_lines, ["domanda", "domande", "q&a"]),
        "risks": _matching_lines(body_lines, ["rischio", "rischi", "blocco", "blocchi"]),
        "followups": _matching_lines(
            body_lines,
            ["follow-up", "followup", "prossimi passi", "next step"],
        ),
        "source_limitations": [
            "Analisi basata solo sul testo della trascrizione fornita."
        ],
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _markdown_list(items: list) -> str:
    if not items:
        return f"- {NOT_DETECTED}"

    lines = []
    for item in items:
        if isinstance(item, dict):
            description = item.get("description", NOT_DETECTED)
            owner = item.get("owner", NOT_DETECTED)
            due_date = item.get("due_date", NOT_DETECTED)
            lines.append(
                f"- {description} | owner: {owner} | due_date: {due_date}"
            )
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def write_markdown(path: Path, analysis: dict, classification: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    markdown = f"""# Transcript Analysis

## Classification

- Type: {classification["type"]}
- Confidence: {classification["confidence"]}
- Secondary type: {classification["secondary_type"]}
- Signals: {", ".join(classification["signals"]) or NOT_DETECTED}
- Reason: {classification["reason"]}
- Recommended recipe: {classification["recommended_recipe"]}

## Summary

{analysis["summary"]}

## Key Points

{_markdown_list(analysis["key_points"])}

## Facts

{_markdown_list(analysis["facts"])}

## Interpretations

{_markdown_list(analysis["interpretations"])}

## Decisions

{_markdown_list(analysis["decisions"])}

## Action Items

{_markdown_list(analysis["action_items"])}

## Open Questions

{_markdown_list(analysis["open_questions"])}

## Risks

{_markdown_list(analysis["risks"])}

## Follow-ups

{_markdown_list(analysis["followups"])}

## Source Limitations

{_markdown_list(analysis["source_limitations"])}
"""
    path.write_text(markdown, encoding="utf-8")


def main() -> int:
    args = parse_args()
    transcript_path = Path(args.transcript)

    try:
        text = read_transcript(transcript_path)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    classification = classify_transcript(text)
    analysis = build_generic_analysis(text, classification)

    output_stem = transcript_path.stem
    classification_path = OUTPUT_JSON_DIR / f"{output_stem}_classification.json"
    analysis_path = OUTPUT_JSON_DIR / f"{output_stem}_analysis.json"
    markdown_path = OUTPUT_MARKDOWN_DIR / f"{output_stem}_summary.md"

    write_json(classification_path, classification)
    write_json(analysis_path, analysis)
    write_markdown(markdown_path, analysis, classification)

    print("Pipeline completed.")
    print(f"Classification: {classification_path}")
    print(f"Analysis: {analysis_path}")
    print(f"Summary: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
