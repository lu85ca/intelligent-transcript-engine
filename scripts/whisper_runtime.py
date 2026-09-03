"""Resolution and fail-fast checks for the approved local Whisper runtime."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


DEFAULT_WHISPER_PYTHON = Path.home() / ".venvs" / "openai-whisper-official" / "bin" / "python3"
DEFAULT_MODEL = "large-v3"


def resolve_whisper_python() -> Path:
    """Return the configured interpreter without ever falling back to system Python."""
    configured = os.environ.get("WHISPER_PYTHON")
    return Path(configured).expanduser() if configured else DEFAULT_WHISPER_PYTHON


def local_model_path(model: str = DEFAULT_MODEL) -> Path:
    return Path.home() / ".cache" / "whisper" / f"{model}.pt"


def validate_whisper_runtime(model: str = DEFAULT_MODEL) -> Path:
    """Check interpreter, import and model cache before launching transcription."""
    python = resolve_whisper_python()
    if not python.is_file() or not os.access(python, os.X_OK):
        raise RuntimeError(
            "OpenAI Whisper local runtime is unavailable: "
            f"WHISPER_PYTHON/default interpreter is not executable: {python}. "
            "No system-Python fallback, installation, or download was attempted."
        )

    imported = subprocess.run(
        [str(python), "-c", "import whisper"],
        capture_output=True,
        text=True,
        check=False,
    )
    if imported.returncode != 0:
        details = imported.stderr.strip() or imported.stdout.strip()
        suffix = f" ({details})" if details else ""
        raise RuntimeError(
            "OpenAI Whisper local runtime cannot import whisper with "
            f"{python}{suffix}. No installation or download was attempted."
        )

    model_path = local_model_path(model)
    if not model_path.is_file():
        raise RuntimeError(
            f"OpenAI Whisper local model '{model}' is missing from cache: {model_path}. "
            "No download was attempted."
        )
    return python
