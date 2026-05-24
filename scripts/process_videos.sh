#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORCE=false

usage() {
  cat <<'EOF'
Usage: scripts/process_videos.sh [--force]

Run Step 1 preprocessing:
  1. video -> WAV audio
  2. WAV audio -> raw Markdown transcript with MLX Whisper

This script does not invoke Codex and does not run normalization or analysis.
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

if [[ "$FORCE" == true ]]; then
  "$ROOT_DIR/scripts/prepare_video_inputs.sh" --force
  python3 "$ROOT_DIR/scripts/transcribe_audio_mlx.py" --force
else
  "$ROOT_DIR/scripts/prepare_video_inputs.sh"
  python3 "$ROOT_DIR/scripts/transcribe_audio_mlx.py"
fi
