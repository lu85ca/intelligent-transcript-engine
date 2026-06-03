#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORCE=false

usage() {
  cat <<'EOF'
Usage: scripts/prepare_video_inputs.sh [--force]

Extract WAV audio from videos in input/videos/.

Options:
  --force   Overwrite existing WAV files.
  -h, --help
            Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

python3 - "$ROOT_DIR" "$FORCE" <<'PY'
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv"}


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def write_report(
    *,
    report_path: Path,
    root: Path,
    source_video: Path,
    output_audio: Path,
    status: str,
    force: bool,
    command: list[str],
    message: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": status,
        "source_video": rel(source_video, root),
        "output_audio": rel(output_audio, root),
        "force": force,
        "command": command,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "message": message,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def supported_videos(video_dir: Path) -> list[Path]:
    if not video_dir.exists():
        return []
    return sorted(
        [
            path
            for path in video_dir.iterdir()
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        ],
        key=lambda item: item.name.lower(),
    )


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    force = sys.argv[2].lower() == "true"
    video_dir = root / "input" / "videos"
    audio_dir = root / "input" / "audio"
    report_dir = root / "output" / "preprocessing"

    video_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        print("Missing dependency: ffmpeg", file=sys.stderr)
        return 127

    videos = supported_videos(video_dir)
    if not videos:
        print("No supported videos found in input/videos/.")
        return 0

    failed = False
    for video_path in videos:
        base_name = video_path.stem
        audio_path = audio_dir / f"{base_name}.wav"
        report_path = report_dir / f"{base_name}_preprocessing.json"
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            video_path.as_posix(),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            audio_path.as_posix(),
        ]

        if audio_path.exists() and not force:
            print(f"Skipping existing audio: input/audio/{base_name}.wav")
            write_report(
                report_path=report_path,
                root=root,
                source_video=video_path,
                output_audio=audio_path,
                status="skipped_existing",
                force=force,
                command=command,
                message="Audio already exists. Re-run with --force to overwrite.",
            )
            continue

        print(f"Extracting audio: input/videos/{video_path.name} -> input/audio/{base_name}.wav")
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode == 0:
            write_report(
                report_path=report_path,
                root=root,
                source_video=video_path,
                output_audio=audio_path,
                status="ok",
                force=force,
                command=command,
                message="Audio extracted as WAV mono 16 kHz.",
            )
        else:
            failed = True
            if audio_path.exists() and audio_path.stat().st_size == 0:
                audio_path.unlink()
            message = f"ffmpeg failed with exit code {completed.returncode}: {completed.stderr.strip()}"
            print(f"Failed to extract audio from: input/videos/{video_path.name}", file=sys.stderr)
            write_report(
                report_path=report_path,
                root=root,
                source_video=video_path,
                output_audio=audio_path,
                status="error",
                force=force,
                command=command,
                message=message,
            )

    return 1 if failed else 0


raise SystemExit(main())
PY
