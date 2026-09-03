from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import whisper_runtime


class WhisperRuntimeTests(unittest.TestCase):
    def test_missing_interpreter_fails_without_system_python_fallback(self) -> None:
        missing = Path("/not-present/openai-whisper-python")
        with patch.object(whisper_runtime, "resolve_whisper_python", return_value=missing), patch.object(
            whisper_runtime.subprocess, "run"
        ) as run:
            with self.assertRaisesRegex(RuntimeError, "No system-Python fallback"):
                whisper_runtime.validate_whisper_runtime()

        run.assert_not_called()

    def test_missing_model_fails_before_any_download_command(self) -> None:
        python = Path(sys.executable)
        missing_model = Path("/not-present/large-v3.pt")
        completed = subprocess.CompletedProcess([str(python), "-c", "import whisper"], 0, "", "")
        with patch.object(whisper_runtime, "resolve_whisper_python", return_value=python), patch.object(
            whisper_runtime.subprocess, "run", return_value=completed
        ) as run, patch.object(whisper_runtime, "local_model_path", return_value=missing_model):
            with self.assertRaisesRegex(RuntimeError, "No download was attempted"):
                whisper_runtime.validate_whisper_runtime()

        self.assertEqual(run.call_args.args[0], [str(python), "-c", "import whisper"])
