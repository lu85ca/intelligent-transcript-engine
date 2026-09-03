from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "start_transcription_batch",
    ROOT / "scripts" / "start_transcription_batch.py",
)
start_transcription_batch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["start_transcription_batch"] = start_transcription_batch
SPEC.loader.exec_module(start_transcription_batch)


class FakeProcess:
    def __init__(self, pid: int = 12345) -> None:
        self.pid = pid


class StartTranscriptionBatchTests(unittest.TestCase):
    def args(self, **overrides) -> argparse.Namespace:
        values = {
            "log": "output/transcription/test_batch.log",
            "pid_file": "output/transcription/test_batch.pid",
            "force": False,
            "json": False,
            "dry_run": False,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def write_audio(self, root: Path, basename: str, raw: bool = False) -> None:
        audio = root / "input" / "audio" / f"{basename}.wav"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(b"fake wav")
        if raw:
            raw_path = root / "input" / "transcripts" / "raw" / f"{basename}_raw.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("raw", encoding="utf-8")

    def test_dry_run_lists_only_pending_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_audio(root, "done", raw=True)
            self.write_audio(root, "todo", raw=False)

            report, code = start_transcription_batch.start_batch(self.args(dry_run=True), root)

            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "dry_run")
            self.assertEqual(report["pending_count"], 1)
            self.assertEqual(report["pending_audio"], ["input/audio/todo.wav"])

    def test_start_writes_pid_file_and_returns_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_audio(root, "todo", raw=False)

            configured_python = Path("/configured/openai-whisper/bin/python3")
            with patch.object(start_transcription_batch, "validate_whisper_runtime", return_value=configured_python), patch.object(
                start_transcription_batch.subprocess, "Popen", return_value=FakeProcess(24680)
            ) as popen:
                report, code = start_transcription_batch.start_batch(self.args(), root)

            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "started")
            self.assertEqual(report["pid"], 24680)
            self.assertTrue((root / "output" / "transcription" / "test_batch.pid").exists())
            self.assertIn("check_process", report["commands_to_check"])
            self.assertIn("next_message_to_codex", report)
            self.assertEqual(popen.call_args.args[0][0], str(configured_python))
            self.assertIn("transcribe_audio_whisper.py", popen.call_args.args[0][1])

    def test_runtime_failure_does_not_start_or_fall_back_to_system_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_audio(root, "todo", raw=False)

            with patch.object(
                start_transcription_batch,
                "validate_whisper_runtime",
                side_effect=RuntimeError("model is missing; no download was attempted"),
            ), patch.object(start_transcription_batch.subprocess, "Popen") as popen:
                report, code = start_transcription_batch.start_batch(self.args(), root)

            self.assertEqual(code, 1)
            self.assertEqual(report["status"], "runtime_unavailable")
            self.assertIn("no download was attempted", report["notes"][-1])
            popen.assert_not_called()

    def test_existing_running_process_is_not_started_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_audio(root, "todo", raw=False)
            pid_file = root / "output" / "transcription" / "test_batch.pid"
            pid_file.parent.mkdir(parents=True)
            pid_file.write_text("111\n", encoding="utf-8")

            with patch.object(start_transcription_batch, "process_is_running", return_value=True), patch.object(
                start_transcription_batch.subprocess, "Popen"
            ) as popen:
                report, code = start_transcription_batch.start_batch(self.args(), root)

            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "already_running")
            self.assertEqual(report["pid"], 111)
            popen.assert_not_called()

    def test_nothing_to_transcribe_when_all_raw_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_audio(root, "done", raw=True)

            report, code = start_transcription_batch.start_batch(self.args(), root)

            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "nothing_to_transcribe")
            self.assertEqual(report["pending_count"], 0)


if __name__ == "__main__":
    unittest.main()
