#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any


DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
DEFAULT_LANGUAGE = "it"
INTRO_WINDOW_SECONDS = 180.0
SHORT_PHRASE_MAX_WORDS = 8
REPEATED_PHRASE_MIN_RUN = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe WAV audio files with MLX Whisper into raw Markdown transcripts."
    )
    parser.add_argument(
        "audio",
        nargs="?",
        help="Optional single audio file to transcribe. Defaults to all .wav files in input/audio/.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"MLX Whisper model to use. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Transcription language. Default: {DEFAULT_LANGUAGE}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing raw Markdown transcripts.",
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


def audio_duration_seconds(audio_path: Path) -> float | None:
    try:
        with contextlib.closing(wave.open(str(audio_path), "rb")) as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            if frames > 0 and rate > 0:
                return frames / float(rate)
    except (wave.Error, OSError):
        return None
    return None


def segment_end_duration(segments: list[dict[str, Any]]) -> float | None:
    for segment in reversed(segments):
        end = segment.get("end")
        if isinstance(end, (int, float)):
            return float(end)
    return None


def resolve_duration(audio_path: Path, result: dict[str, Any]) -> float | None:
    duration = audio_duration_seconds(audio_path)
    if duration is not None:
        return duration

    result_duration = result.get("duration")
    if isinstance(result_duration, (int, float)):
        return float(result_duration)

    segments = result.get("segments")
    if isinstance(segments, list):
        return segment_end_duration([s for s in segments if isinstance(s, dict)])

    return None


def normalize_phrase_for_check(phrase: str) -> str:
    normalized = phrase.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[\s\.,;:!\?]+$", "", normalized)
    return normalized


def is_short_phrase(phrase: str) -> bool:
    words = [w for w in phrase.split() if w]
    return 0 < len(words) <= SHORT_PHRASE_MAX_WORDS


def phrases_match(left: str, right: str) -> bool:
    if left == right:
        return True
    if not left or not right:
        return False
    return SequenceMatcher(None, left, right).ratio() >= 0.92


def sentence_units_from_text(text: str) -> list[dict[str, Any]]:
    parts = re.findall(r"[^.!?\n]+[.!?]?", text)
    units: list[dict[str, Any]] = []
    for part in parts:
        phrase = part.strip()
        normalized = normalize_phrase_for_check(phrase)
        if phrase and is_short_phrase(normalized):
            units.append(
                {
                    "phrase": phrase,
                    "normalized": normalized,
                    "start": None,
                    "end": None,
                }
            )
    return units


def sentence_units_from_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = segment.get("start")
        end = segment.get("end")
        for unit in sentence_units_from_text(text):
            unit["start"] = float(start) if isinstance(start, (int, float)) else None
            unit["end"] = float(end) if isinstance(end, (int, float)) else None
            units.append(unit)
    return units


def repeated_runs(units: list[dict[str, Any]], min_run: int) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    for unit in units:
        if not unit.get("normalized"):
            continue
        if not current:
            current = [unit]
            continue

        if phrases_match(str(current[-1]["normalized"]), str(unit["normalized"])):
            current.append(unit)
        else:
            if len(current) >= min_run:
                runs.append(build_run(current))
            current = [unit]

    if len(current) >= min_run:
        runs.append(build_run(current))

    return runs


def build_run(run_units: list[dict[str, Any]]) -> dict[str, Any]:
    starts = [u["start"] for u in run_units if isinstance(u.get("start"), float)]
    ends = [u["end"] for u in run_units if isinstance(u.get("end"), float)]
    phrase = str(run_units[0]["phrase"]).strip()
    return {
        "phrase": phrase,
        "evidence": " ".join(str(u["phrase"]).strip() for u in run_units[:6]),
        "count": len(run_units),
        "start": min(starts) if starts else None,
        "end": max(ends) if ends else None,
    }


def technical_duration(run: dict[str, Any]) -> float | None:
    start = run.get("start")
    end = run.get("end")
    if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start:
        return float(end) - float(start)
    return None


def warning_from_run(run: dict[str, Any]) -> dict[str, Any]:
    duration = technical_duration(run)
    count = int(run["count"])
    severity = "high" if count >= 10 or (duration is not None and duration >= 60.0) else "warning"
    return {
        "type": "repeated_phrase",
        "severity": severity,
        "message": f"Repeated short phrase detected {count} consecutive times.",
        "evidence": run["evidence"],
        "start": run.get("start"),
        "end": run.get("end"),
        "suggested_action": "review raw transcript before analysis",
    }


def intro_warning(units: list[dict[str, Any]]) -> dict[str, Any] | None:
    intro_units = [
        unit
        for unit in units
        if unit.get("start") is None or float(unit["start"]) <= INTRO_WINDOW_SECONDS
    ]
    runs = repeated_runs(intro_units, REPEATED_PHRASE_MIN_RUN)
    if not runs:
        return None
    run = max(runs, key=lambda item: int(item["count"]))
    duration = technical_duration(run)
    severity = "high" if int(run["count"]) >= 10 or (duration is not None and duration >= 60.0) else "warning"
    return {
        "type": "possible_intro_loop",
        "severity": severity,
        "message": "Repeated short phrase detected near the beginning of the transcript.",
        "evidence": run["phrase"],
        "start": run.get("start"),
        "end": run.get("end"),
        "suggested_action": "review or manually trim non-informative intro before analysis",
    }


def outro_warning(units: list[dict[str, Any]], duration: float | None) -> dict[str, Any] | None:
    if not units:
        return None

    if duration is not None:
        outro_units = [
            unit
            for unit in units
            if unit.get("end") is None or float(unit["end"]) >= max(0.0, duration - 180.0)
        ]
    else:
        outro_units = units[-30:]

    runs = repeated_runs(outro_units, 2)
    if not runs:
        return None
    run = max(runs, key=lambda item: int(item["count"]))
    return {
        "type": "possible_outro_repetition",
        "severity": "info",
        "message": "Repeated short phrase detected near the end of the transcript.",
        "evidence": run["evidence"],
        "start": run.get("start"),
        "end": run.get("end"),
        "suggested_action": "review outro before analysis if needed",
    }


def quality_warnings_for_transcript(text: str, result: dict[str, Any], duration: float | None) -> list[dict[str, Any]]:
    raw_segments = result.get("segments")
    segments = [s for s in raw_segments if isinstance(s, dict)] if isinstance(raw_segments, list) else []
    units = sentence_units_from_segments(segments) if segments else sentence_units_from_text(text)

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for run in repeated_runs(units, REPEATED_PHRASE_MIN_RUN):
        warning = warning_from_run(run)
        key = (warning["type"], str(warning["evidence"]))
        if key not in seen:
            warnings.append(warning)
            seen.add(key)

    for warning in (intro_warning(units), outro_warning(units, duration)):
        if warning is None:
            continue
        key = (warning["type"], str(warning["evidence"]))
        if key not in seen:
            warnings.append(warning)
            seen.add(key)

    return warnings


def normalization_candidates_for_text(text: str) -> list[dict[str, Any]]:
    checks = [
        (
            r"\bBLM\b",
            "BLM",
            "LLM",
            "medium",
            "Observed in AI/webinar context; possible confusion with LLM requires manual review.",
        ),
        (
            r"\bCoppale\b",
            "Coppale",
            "Copilot",
            "medium",
            "Observed as a possible variant of Copilot; requires manual review.",
        ),
        (
            r"\bCopario\s+Chat\b",
            "Copario Chat",
            "Copilot Chat",
            "medium",
            "Observed as a possible variant of Copilot Chat; requires manual review.",
        ),
    ]

    candidates: list[dict[str, Any]] = []
    for pattern, observed, canonical, confidence, reason in checks:
        if re.search(pattern, text, flags=re.IGNORECASE):
            candidates.append(
                {
                    "observed": observed,
                    "possible_canonical": canonical,
                    "confidence": confidence,
                    "reason": reason,
                    "action": "candidate_only_do_not_auto_replace",
                }
            )
    return candidates


def safe_for_analysis(quality_warnings: list[dict[str, Any]], status: str) -> bool:
    if status == "error":
        return False
    high_warnings = [warning for warning in quality_warnings if warning.get("severity") == "high"]
    if high_warnings:
        return False
    repeated_warnings = [
        warning
        for warning in quality_warnings
        if warning.get("type") in {"repeated_phrase", "possible_intro_loop"}
    ]
    return len(repeated_warnings) < 3


def technical_report(
    *,
    root: Path,
    audio_path: Path,
    transcript_path: Path,
    model: str,
    language: str,
    status: str,
    force: bool,
    message: str,
    result: dict[str, Any] | None = None,
    duration: float | None = None,
    quality_warnings: list[dict[str, Any]] | None = None,
    normalization_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = result or {}
    quality_warnings = quality_warnings or []
    normalization_candidates = normalization_candidates or []
    return {
        "status": status,
        "source_audio": rel(audio_path, root),
        "output_transcript": rel(transcript_path, root),
        "transcription_engine": "mlx-whisper",
        "transcription_model": model,
        "language": language,
        "force": force,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "duration": duration if duration is not None else resolve_duration(audio_path, result),
        "segments": result.get("segments", []),
        "quality_warnings": quality_warnings,
        "normalization_candidates": normalization_candidates,
        "safe_for_analysis": safe_for_analysis(quality_warnings, status),
        "message": message,
    }


def skipped_existing_report(
    *,
    root: Path,
    audio_path: Path,
    transcript_path: Path,
    model: str,
    language: str,
    force: bool,
) -> dict[str, Any]:
    return {
        "status": "skipped_existing",
        "source_audio": rel(audio_path, root),
        "output_transcript": rel(transcript_path, root),
        "transcription_engine": "mlx-whisper",
        "transcription_model": model,
        "language": language,
        "force": force,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "duration": None,
        "segments": [],
        "quality_check_performed": False,
        "quality_warnings": [],
        "normalization_candidates": [],
        "safe_for_analysis": None,
        "message": "Existing transcript skipped; no transcription quality check was performed.",
    }


def frontmatter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", " ").strip()


def write_markdown(
    *,
    path: Path,
    root: Path,
    audio_path: Path,
    model: str,
    language: str,
    text: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = text.strip()
    markdown = (
        "---\n"
        "source_type: video_or_audio\n"
        f"source_audio: {frontmatter_value(rel(audio_path, root))}\n"
        "transcription_engine: mlx-whisper\n"
        f"transcription_model: {frontmatter_value(model)}\n"
        f"language: {frontmatter_value(language)}\n"
        "status: raw_transcript\n"
        "---\n\n"
        "# Trascrizione grezza\n\n"
        f"{body}\n"
    )
    path.write_text(markdown, encoding="utf-8")


def collect_audio_files(root: Path, audio_arg: str | None) -> list[Path]:
    if audio_arg:
        return [Path(audio_arg).expanduser().resolve()]

    audio_dir = root / "input" / "audio"
    return sorted(audio_dir.glob("*.wav"))


def import_mlx_whisper():
    try:
        import mlx_whisper  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: mlx_whisper. Install it in a Python venv with `pip install mlx-whisper`."
        ) from exc
    return mlx_whisper


def transcribe_one(
    *,
    root: Path,
    audio_path: Path,
    model: str,
    language: str,
    force: bool,
) -> bool:
    raw_dir = root / "input" / "transcripts" / "raw"
    report_dir = root / "output" / "transcription"
    transcript_path = raw_dir / f"{audio_path.stem}_raw.md"
    report_path = report_dir / f"{audio_path.stem}_transcription.json"

    if not audio_path.exists():
        write_json(
            report_path,
            technical_report(
                root=root,
                audio_path=audio_path,
                transcript_path=transcript_path,
                model=model,
                language=language,
                status="error",
                force=force,
                message="Audio file does not exist.",
            ),
        )
        print(f"Missing audio file: {audio_path}", file=sys.stderr)
        return False

    if transcript_path.exists() and not force:
        if report_path.exists():
            print(
                "Skipped existing transcript and kept existing technical report: "
                f"{rel(transcript_path, root)}"
            )
        else:
            write_json(
                report_path,
                skipped_existing_report(
                    root=root,
                    audio_path=audio_path,
                    transcript_path=transcript_path,
                    model=model,
                    language=language,
                    force=force,
                ),
            )
            print(
                "Existing transcript skipped; no transcription quality check was performed: "
                f"{rel(transcript_path, root)}"
            )
        return True

    try:
        mlx_whisper = import_mlx_whisper()
    except RuntimeError as exc:
        write_json(
            report_path,
            technical_report(
                root=root,
                audio_path=audio_path,
                transcript_path=transcript_path,
                model=model,
                language=language,
                status="error",
                force=force,
                message=str(exc),
            ),
        )
        print(str(exc), file=sys.stderr)
        return False

    print(f"Transcribing: {rel(audio_path, root)}")
    try:
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=model,
            language=language,
        )
    except Exception as exc:  # noqa: BLE001 - report external transcription failures clearly.
        write_json(
            report_path,
            technical_report(
                root=root,
                audio_path=audio_path,
                transcript_path=transcript_path,
                model=model,
                language=language,
                status="error",
                force=force,
                message=f"MLX Whisper transcription failed: {exc}",
            ),
        )
        print(f"Failed to transcribe {rel(audio_path, root)}: {exc}", file=sys.stderr)
        return False

    text = str(result.get("text", "")).strip()
    duration = resolve_duration(audio_path, result)
    quality_warnings = quality_warnings_for_transcript(text, result, duration)
    normalization_candidates = normalization_candidates_for_text(text)

    write_markdown(
        path=transcript_path,
        root=root,
        audio_path=audio_path,
        model=model,
        language=language,
        text=text,
    )
    write_json(
        report_path,
        technical_report(
            root=root,
            audio_path=audio_path,
            transcript_path=transcript_path,
            model=model,
            language=language,
            status="ok",
            force=force,
            message="Raw transcript written without timestamps in Markdown body.",
            result=result,
            duration=duration,
            quality_warnings=quality_warnings,
            normalization_candidates=normalization_candidates,
        ),
    )
    return True


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    (root / "input" / "audio").mkdir(parents=True, exist_ok=True)
    (root / "input" / "transcripts" / "raw").mkdir(parents=True, exist_ok=True)
    (root / "output" / "transcription").mkdir(parents=True, exist_ok=True)

    audio_files = collect_audio_files(root, args.audio)
    if not audio_files:
        print("No WAV audio files found in input/audio/.")
        return 0

    success = True
    for audio_path in audio_files:
        if audio_path.suffix.lower() != ".wav":
            print(f"Skipping non-WAV audio file: {audio_path}", file=sys.stderr)
            success = False
            continue
        success = transcribe_one(
            root=root,
            audio_path=audio_path,
            model=args.model,
            language=args.language,
            force=args.force,
        ) and success

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
