#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VIDEO_DIR="$ROOT_DIR/input/videos"
AUDIO_DIR="$ROOT_DIR/input/audio"
REPORT_DIR="$ROOT_DIR/output/preprocessing"

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

mkdir -p "$VIDEO_DIR" "$AUDIO_DIR" "$REPORT_DIR"

write_report() {
  local report_path="$1"
  local input_video="$2"
  local output_audio="$3"
  local status="$4"
  local message="$5"
  shift 5

  python3 - "$report_path" "$ROOT_DIR" "$input_video" "$output_audio" "$status" "$FORCE" "$message" "$@" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

report_path, root_dir, input_video, output_audio, status, force, message, *command = sys.argv[1:]

def rel(path):
    if not path:
        return ""
    try:
        return os.path.relpath(path, root_dir)
    except ValueError:
        return path

report = {
    "status": status,
    "source_video": rel(input_video),
    "output_audio": rel(output_audio),
    "force": force.lower() == "true",
    "command": command,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "message": message,
}

os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY
}

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Missing dependency: ffmpeg" >&2
  exit 127
fi

found=0
failed=0

while IFS= read -r -d '' video_path; do
  found=1
  video_file="$(basename "$video_path")"
  base_name="${video_file%.*}"
  audio_path="$AUDIO_DIR/$base_name.wav"
  report_path="$REPORT_DIR/${base_name}_preprocessing.json"
  command=(ffmpeg -hide_banner -loglevel error -y -i "$video_path" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$audio_path")

  if [[ -f "$audio_path" && "$FORCE" != true ]]; then
    echo "Skipping existing audio: input/audio/$base_name.wav"
    write_report "$report_path" "$video_path" "$audio_path" "skipped_existing" "Audio already exists. Re-run with --force to overwrite." "${command[@]}"
    continue
  fi

  echo "Extracting audio: input/videos/$video_file -> input/audio/$base_name.wav"
  ffmpeg_output="$("${command[@]}" 2>&1)"
  exit_code=$?

  if [[ $exit_code -eq 0 ]]; then
    write_report "$report_path" "$video_path" "$audio_path" "ok" "Audio extracted as WAV mono 16 kHz." "${command[@]}"
  else
    failed=1
    echo "Failed to extract audio from: input/videos/$video_file" >&2
    write_report "$report_path" "$video_path" "$audio_path" "error" "ffmpeg failed with exit code $exit_code: $ffmpeg_output" "${command[@]}"
  fi
done < <(find "$VIDEO_DIR" -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.m4v' -o -iname '*.mkv' \) -print0)

if [[ $found -eq 0 ]]; then
  echo "No supported videos found in input/videos/."
fi

exit "$failed"
