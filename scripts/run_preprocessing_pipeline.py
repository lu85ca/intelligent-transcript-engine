#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_CONTEXTS = {
    "work_meetings",
    "macro_categories/finance",
    "macro_categories/travel",
    "macro_categories/social_media_management",
    "macro_categories/generic",
}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv"}
AUDIO_EXTENSIONS = {".wav"}
RAW_SUFFIX = "_raw.md"
REVIEWED_SUFFIX = "_reviewed.md"
NORMALIZED_SUFFIX = "_normalized.md"

STATUS_READY = "ready_for_agent_analysis"
STATUS_REVIEW = "requires_manual_review"
STATUS_FAILED = "failed"

NEXT_READY = "Run the agent-driven transcript intelligence workflow on selected_transcript."
NEXT_REVIEW = "Review the transcript before generating the final summary."
NEXT_FAILED = "Fix the failed preprocessing step and rerun the pipeline."

MSG_NO_INPUT = "Provide a basename/path or use --latest-video."
MSG_NO_LATEST_VIDEO = "No supported videos found in input/videos/."
MSG_UNSUPPORTED_INPUT = "Unsupported input path. Use a basename, supported video path, or WAV audio path."
MSG_NO_CODEX = "This runner does not invoke Codex CLI or generate final analysis outputs."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic preprocessing through transcript selection for agent-driven analysis."
    )
    parser.add_argument("input", nargs="?", help="Transcript basename, video path, or WAV audio path.")
    parser.add_argument("--latest-video", action="store_true", help="Use the newest supported file in input/videos/.")
    parser.add_argument(
        "--context",
        default="work_meetings",
        choices=sorted(ALLOWED_CONTEXTS),
        help="Knowledge context. Default: work_meetings.",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate outputs for steps that support it.")
    parser.add_argument(
        "--apply-safe-cleanup",
        action="store_true",
        help="Pass --apply-safe-cleanup to the reviewed transcript step.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show the plan without executing steps or writing files.")
    parser.add_argument("--json", action="store_true", help="Print the full pipeline report as JSON.")
    parser.add_argument("--verbose", action="store_true", help="Print subprocess diagnostics to stderr.")
    parser.add_argument("--skip-transcription", action="store_true", help="Do not run Step 1.")
    parser.add_argument("--skip-candidates", action="store_true", help="Do not run candidate collection.")
    return parser.parse_args()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def strip_known_suffix(name: str) -> str:
    for suffix in (NORMALIZED_SUFFIX, REVIEWED_SUFFIX, RAW_SUFFIX):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    if name.endswith(".md"):
        return name[:-3]
    return name


def transcript_paths(root: Path, basename: str) -> dict[str, Path]:
    return {
        "raw": root / "input" / "transcripts" / "raw" / f"{basename}{RAW_SUFFIX}",
        "reviewed": root / "input" / "transcripts" / "reviewed" / f"{basename}{REVIEWED_SUFFIX}",
        "normalized": root / "input" / "transcripts" / "normalized" / f"{basename}{NORMALIZED_SUFFIX}",
        "transcription_report": root / "output" / "transcription" / f"{basename}_transcription.json",
        "review_report": root / "output" / "review" / f"{basename}_review.json",
        "normalization_report": root / "output" / "normalization" / f"{basename}_normalization.json",
        "pipeline_report": root / "output" / "pipeline" / f"{basename}_pipeline.json",
    }


def context_path(context: str) -> str:
    if context == "work_meetings":
        return "knowledge/work_meetings"
    return f"knowledge/{context}"


def candidate_file_path(root: Path, context: str, basename: str) -> Path:
    return root / context_path(context) / "candidates" / f"{basename}_candidates.json"


def supported_videos(root: Path) -> list[Path]:
    video_dir = root / "input" / "videos"
    if not video_dir.exists():
        return []
    return sorted(
        [path for path in video_dir.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def video_for_basename(root: Path, basename: str) -> Path | None:
    video_dir = root / "input" / "videos"
    for extension in sorted(VIDEO_EXTENSIONS):
        candidate = video_dir / f"{basename}{extension}"
        if candidate.exists():
            return candidate
    return None


def copy_into(path: Path, target_dir: Path, root: Path, dry_run: bool) -> Path:
    target = target_dir / path.name
    if dry_run:
        return target
    target_dir.mkdir(parents=True, exist_ok=True)
    if path.resolve() != target.resolve():
        shutil.copy2(path, target)
    return target


def resolve_input(args: argparse.Namespace, root: Path) -> tuple[dict[str, Any], str]:
    if args.latest_video:
        videos = supported_videos(root)
        if not videos:
            raise ValueError(MSG_NO_LATEST_VIDEO)
        source = videos[0]
        return {
            "input_arg": "--latest-video",
            "input_type": "latest_video",
            "source_video": rel(source, root),
            "source_audio": None,
            "copied_to": None,
        }, source.stem

    if not args.input:
        raise ValueError(MSG_NO_INPUT)

    value = args.input
    path = Path(value).expanduser()
    looks_like_path = path.suffix or "/" in value

    if looks_like_path:
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            raise ValueError(f"Input path not found: {rel(path, root)}")
        suffix = path.suffix.lower()
        if suffix in VIDEO_EXTENSIONS:
            target = copy_into(path, root / "input" / "videos", root, args.dry_run)
            return {
                "input_arg": value,
                "input_type": "video",
                "source_video": rel(target, root),
                "source_audio": None,
                "copied_to": rel(target, root) if target.resolve() != path.resolve() else None,
            }, target.stem
        if suffix in AUDIO_EXTENSIONS:
            target = copy_into(path, root / "input" / "audio", root, args.dry_run)
            return {
                "input_arg": value,
                "input_type": "audio",
                "source_video": None,
                "source_audio": rel(target, root),
                "copied_to": rel(target, root) if target.resolve() != path.resolve() else None,
            }, target.stem
        if suffix == ".md":
            return {
                "input_arg": value,
                "input_type": "transcript_path",
                "source_video": None,
                "source_audio": None,
                "copied_to": None,
            }, strip_known_suffix(path.name)
        raise ValueError(MSG_UNSUPPORTED_INPUT)

    source_video = video_for_basename(root, value)
    source_audio = root / "input" / "audio" / f"{value}.wav"
    return {
        "input_arg": value,
        "input_type": "basename",
        "source_video": rel(source_video, root) if source_video else None,
        "source_audio": rel(source_audio, root) if source_audio.exists() else None,
        "copied_to": None,
    }, strip_known_suffix(value)


def command_for_display(command: list[str], root: Path) -> list[str]:
    display: list[str] = []
    for item in command:
        path = Path(item)
        if path.is_absolute():
            display.append(rel(path, root))
        else:
            display.append(item)
    return display


def run_command(command: list[str], *, root: Path, verbose: bool) -> subprocess.CompletedProcess[str]:
    if verbose:
        print("Running: " + " ".join(command_for_display(command, root)), file=sys.stderr)
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    if verbose and completed.stdout:
        print(completed.stdout, file=sys.stderr, end="" if completed.stdout.endswith("\n") else "\n")
    if verbose and completed.stderr:
        print(completed.stderr, file=sys.stderr, end="" if completed.stderr.endswith("\n") else "\n")
    return completed


def step_payload(name: str, status: str, command: list[str] | None, outputs: list[str], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "status": status,
        "command": command,
        "outputs": outputs,
    }
    payload.update(extra)
    return payload


def step1_command(root: Path, input_info: dict[str, Any], basename: str, force: bool) -> list[str]:
    if input_info["input_type"] == "audio":
        command = ["python3", str(root / "scripts" / "transcribe_audio_mlx.py"), str(root / "input" / "audio" / f"{basename}.wav")]
        if force:
            command.append("--force")
        return command

    audio_path = root / "input" / "audio" / f"{basename}.wav"
    if input_info["input_type"] in {"basename", "transcript_path"} and audio_path.exists():
        command = ["python3", str(root / "scripts" / "transcribe_audio_mlx.py"), str(audio_path)]
        if force:
            command.append("--force")
        return command

    command = [str(root / "scripts" / "process_videos.sh")]
    if force:
        command.append("--force")
    return command


def run_preprocessing_pipeline(args: argparse.Namespace, root: Path) -> tuple[dict[str, Any], int]:
    warnings: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    basename = ""
    report_path: Path | None = None

    try:
        input_info, basename = resolve_input(args, root)
    except ValueError as exc:
        report = base_report(
            basename="",
            input_info={"input_arg": args.input or "--latest-video", "input_type": "unknown"},
            context=args.context,
            warnings=[],
        )
        report.update(
            {
                "pipeline_status": STATUS_FAILED,
                "ready_for_agent_analysis": False,
                "requires_manual_review": False,
                "reason": str(exc),
                "next_action": NEXT_FAILED,
            }
        )
        return report, 2

    paths = transcript_paths(root, basename)
    paths["candidate_file"] = candidate_file_path(root, args.context, basename)
    report_path = paths["pipeline_report"]
    report = base_report(basename=basename, input_info=input_info, context=args.context, warnings=warnings)
    report["reports"] = {
        "transcription": rel(paths["transcription_report"], root),
        "review": rel(paths["review_report"], root),
        "normalization": rel(paths["normalization_report"], root),
        "candidates": rel(paths["candidate_file"], root),
        "selection": None,
    }

    if args.dry_run:
        steps.extend(build_dry_run_steps(root, args, input_info, basename, paths))
        report.update(
            {
                "pipeline_status": "dry_run",
                "ready_for_agent_analysis": False,
                "requires_manual_review": False,
                "selected_transcript": None,
                "selected_level": None,
                "steps": steps,
                "next_action": "Review the plan, then rerun without --dry-run.",
            }
        )
        return report, 0

    # Step 1
    raw_ready = paths["raw"].exists() and paths["transcription_report"].exists()
    if args.skip_transcription and not raw_ready:
        steps.append(
            step_payload(
                "transcription",
                "failed",
                None,
                [rel(paths["raw"], root), rel(paths["transcription_report"], root)],
                message="--skip-transcription was requested but raw transcript/report are missing.",
            )
        )
        return finalize_failure(report, steps, report_path, "Raw transcript/report missing while transcription is skipped.")
    if raw_ready and not args.force:
        steps.append(
            step_payload(
                "transcription",
                "skipped_existing_output",
                None,
                [rel(paths["raw"], root), rel(paths["transcription_report"], root)],
            )
        )
    elif args.skip_transcription:
        steps.append(
            step_payload(
                "transcription",
                "skipped",
                None,
                [rel(paths["raw"], root), rel(paths["transcription_report"], root)],
            )
        )
    else:
        command = step1_command(root, input_info, basename, args.force)
        completed = run_command(command, root=root, verbose=args.verbose)
        status = "completed" if completed.returncode == 0 and paths["raw"].exists() and paths["transcription_report"].exists() else "failed"
        steps.append(
            step_payload(
                "transcription",
                status,
                command_for_display(command, root),
                [rel(paths["raw"], root), rel(paths["transcription_report"], root)],
                returncode=completed.returncode,
            )
        )
        if status == "failed":
            return finalize_failure(report, steps, report_path, "Step 1 transcription/preprocessing failed.")

    # Step 2
    review_ready = paths["reviewed"].exists() and paths["review_report"].exists()
    if review_ready and not args.force:
        steps.append(
            step_payload(
                "review",
                "skipped_existing_output",
                None,
                [rel(paths["reviewed"], root), rel(paths["review_report"], root)],
            )
        )
    else:
        if not paths["raw"].exists():
            steps.append(step_payload("review", "failed", None, [rel(paths["reviewed"], root), rel(paths["review_report"], root)]))
            return finalize_failure(report, steps, report_path, "Raw transcript missing before review step.")
        command = ["python3", str(root / "scripts" / "prepare_review_transcript.py"), str(paths["raw"])]
        if args.apply_safe_cleanup:
            command.append("--apply-safe-cleanup")
        completed = run_command(command, root=root, verbose=args.verbose)
        status = "completed" if completed.returncode == 0 and paths["reviewed"].exists() and paths["review_report"].exists() else "failed"
        steps.append(
            step_payload(
                "review",
                status,
                command_for_display(command, root),
                [rel(paths["reviewed"], root), rel(paths["review_report"], root)],
                returncode=completed.returncode,
                apply_safe_cleanup=args.apply_safe_cleanup,
            )
        )
        if status == "failed":
            return finalize_failure(report, steps, report_path, "Step 2 review failed.")

    # Step 3
    normalization_ready = paths["normalized"].exists() and paths["normalization_report"].exists()
    if normalization_ready and not args.force:
        steps.append(
            step_payload(
                "normalization",
                "skipped_existing_output",
                None,
                [rel(paths["normalized"], root), rel(paths["normalization_report"], root)],
            )
        )
    else:
        command = [
            "python3",
            str(root / "scripts" / "normalize_transcript.py"),
            basename,
            "--context",
            args.context,
        ]
        if args.force:
            command.append("--force")
        completed = run_command(command, root=root, verbose=args.verbose)
        status = "completed" if completed.returncode == 0 and paths["normalized"].exists() and paths["normalization_report"].exists() else "failed"
        steps.append(
            step_payload(
                "normalization",
                status,
                command_for_display(command, root),
                [rel(paths["normalized"], root), rel(paths["normalization_report"], root)],
                returncode=completed.returncode,
            )
        )
        if status == "failed":
            return finalize_failure(report, steps, report_path, "Step 3 normalization failed.")

    # Step 4
    candidate_count = 0
    if args.skip_candidates:
        steps.append(step_payload("candidate_collection", "skipped", None, [rel(paths["candidate_file"], root)]))
    else:
        command = [
            "python3",
            str(root / "scripts" / "manage_candidates.py"),
            "collect",
            basename,
            "--context",
            args.context,
            "--json",
        ]
        if args.force:
            command.append("--force")
        completed = run_command(command, root=root, verbose=args.verbose)
        candidate_payload = parse_json_stdout(completed.stdout)
        candidate_count = int(candidate_payload.get("candidate_count", 0)) if candidate_payload else 0
        status = "completed" if completed.returncode == 0 and candidate_payload is not None else "failed"
        steps.append(
            step_payload(
                "candidate_collection",
                status,
                command_for_display(command, root),
                [rel(paths["candidate_file"], root)],
                returncode=completed.returncode,
                candidate_count=candidate_count,
            )
        )
        if status == "failed":
            return finalize_failure(report, steps, report_path, "Step 4 candidate collection failed.")

    # Step 5
    command = ["python3", str(root / "scripts" / "select_analysis_transcript.py"), basename, "--json"]
    completed = run_command(command, root=root, verbose=args.verbose)
    selection = parse_json_stdout(completed.stdout)
    if selection is None:
        steps.append(
            step_payload(
                "transcript_selection",
                "failed",
                command_for_display(command, root),
                [],
                returncode=completed.returncode,
            )
        )
        return finalize_failure(report, steps, report_path, "Step 5 transcript selection did not return valid JSON.")

    selection_status = "completed" if selection.get("decision") else "failed"
    steps.append(
        step_payload(
            "transcript_selection",
            selection_status,
            command_for_display(command, root),
            [selection["selected_transcript"]] if selection.get("selected_transcript") else [],
            returncode=completed.returncode,
            decision=selection.get("decision"),
        )
    )

    selected = selection.get("selected_transcript")
    selected_level = selection.get("selected_level")
    requires_review = bool(selection.get("requires_review"))
    ready = bool(selected) and not requires_review and (root / str(selected)).exists()
    status = STATUS_READY if ready else STATUS_REVIEW
    code = 0 if ready else 1
    reason = selection.get("reason")

    report.update(
        {
            "pipeline_status": status,
            "ready_for_agent_analysis": ready,
            "requires_manual_review": not ready,
            "selected_transcript": selected if ready else None,
            "selected_level": selected_level if ready else None,
            "safe_for_analysis": selection.get("safe_for_analysis"),
            "selection_decision": selection.get("decision"),
            "reason": None if ready else reason,
            "steps": steps,
            "candidate_count": candidate_count,
            "next_action": NEXT_READY if ready else NEXT_REVIEW,
        }
    )
    write_json(report_path, report)
    return report, code


def parse_json_stdout(stdout: str) -> dict[str, Any] | None:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def base_report(*, basename: str, input_info: dict[str, Any], context: str, warnings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "basename": basename,
        "input": input_info,
        "context": context,
        "pipeline_status": None,
        "ready_for_agent_analysis": False,
        "requires_manual_review": False,
        "selected_transcript": None,
        "selected_level": None,
        "steps": [],
        "reports": {},
        "candidate_count": 0,
        "warnings": warnings,
        "next_action": None,
        "created_at": now_iso(),
        "notes": [MSG_NO_CODEX],
    }


def build_dry_run_steps(
    root: Path,
    args: argparse.Namespace,
    input_info: dict[str, Any],
    basename: str,
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    raw_ready = paths["raw"].exists() and paths["transcription_report"].exists()
    review_ready = paths["reviewed"].exists() and paths["review_report"].exists()
    normalization_ready = paths["normalized"].exists() and paths["normalization_report"].exists()

    return [
        step_payload(
            "transcription",
            "skipped_existing_output" if raw_ready and not args.force else "planned",
            None if raw_ready and not args.force else command_for_display(step1_command(root, input_info, basename, args.force), root),
            [rel(paths["raw"], root), rel(paths["transcription_report"], root)],
        ),
        step_payload(
            "review",
            "skipped_existing_output" if review_ready and not args.force else "planned",
            None
            if review_ready and not args.force
            else command_for_display(
                [
                    "python3",
                    str(root / "scripts" / "prepare_review_transcript.py"),
                    str(paths["raw"]),
                    *(["--apply-safe-cleanup"] if args.apply_safe_cleanup else []),
                ],
                root,
            ),
            [rel(paths["reviewed"], root), rel(paths["review_report"], root)],
        ),
        step_payload(
            "normalization",
            "skipped_existing_output" if normalization_ready and not args.force else "planned",
            None
            if normalization_ready and not args.force
            else command_for_display(
                [
                    "python3",
                    str(root / "scripts" / "normalize_transcript.py"),
                    basename,
                    "--context",
                    args.context,
                    *(["--force"] if args.force else []),
                ],
                root,
            ),
            [rel(paths["normalized"], root), rel(paths["normalization_report"], root)],
        ),
        step_payload(
            "candidate_collection",
            "skipped" if args.skip_candidates else "planned",
            None
            if args.skip_candidates
            else command_for_display(
                [
                    "python3",
                    str(root / "scripts" / "manage_candidates.py"),
                    "collect",
                    basename,
                    "--context",
                    args.context,
                    "--json",
                    *(["--force"] if args.force else []),
                ],
                root,
            ),
            [rel(paths["candidate_file"], root)],
        ),
        step_payload(
            "transcript_selection",
            "planned",
            command_for_display(
                ["python3", str(root / "scripts" / "select_analysis_transcript.py"), basename, "--json"],
                root,
            ),
            [],
        ),
    ]


def finalize_failure(
    report: dict[str, Any],
    steps: list[dict[str, Any]],
    report_path: Path | None,
    reason: str,
) -> tuple[dict[str, Any], int]:
    report.update(
        {
            "pipeline_status": STATUS_FAILED,
            "ready_for_agent_analysis": False,
            "requires_manual_review": False,
            "selected_transcript": None,
            "selected_level": None,
            "steps": steps,
            "reason": reason,
            "next_action": NEXT_FAILED,
        }
    )
    if report_path is not None:
        write_json(report_path, report)
    return report, 1


def main() -> int:
    args = parse_args()
    root = project_root()
    report, code = run_preprocessing_pipeline(args, root)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report.get("ready_for_agent_analysis"):
        print(report["selected_transcript"])
    else:
        print(report.get("reason") or report.get("next_action") or STATUS_FAILED, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
