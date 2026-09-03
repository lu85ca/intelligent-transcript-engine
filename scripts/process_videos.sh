#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORCE=false

usage() {
  cat <<'EOF'
Usage: scripts/process_videos.sh [--force]

Run Step 1 preprocessing:
  1. video -> WAV audio
  2. WAV audio -> raw Markdown transcript with local OpenAI Whisper

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

WHISPER_PYTHON_BIN="${WHISPER_PYTHON:-$HOME/.venvs/openai-whisper-official/bin/python3}"
if [[ ! -x "$WHISPER_PYTHON_BIN" ]]; then
  echo "OpenAI Whisper local runtime is unavailable: $WHISPER_PYTHON_BIN. No fallback, installation, or download was attempted." >&2
  exit 1
fi
if ! "$WHISPER_PYTHON_BIN" -c 'import whisper' >/dev/null 2>&1; then
  echo "OpenAI Whisper local runtime cannot import whisper. No installation or download was attempted." >&2
  exit 1
fi
if [[ ! -f "$HOME/.cache/whisper/large-v3.pt" ]]; then
  echo "OpenAI Whisper local model 'large-v3' is missing from cache. No download was attempted." >&2
  exit 1
fi

if [[ "$FORCE" == true ]]; then
  "$ROOT_DIR/scripts/prepare_video_inputs.sh" --force
  "$WHISPER_PYTHON_BIN" "$ROOT_DIR/scripts/transcribe_audio_whisper.py" --force
else
  "$ROOT_DIR/scripts/prepare_video_inputs.sh"
  "$WHISPER_PYTHON_BIN" "$ROOT_DIR/scripts/transcribe_audio_whisper.py"
fi
