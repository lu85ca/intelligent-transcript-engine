from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("transcribe_audio_whisper", SCRIPTS / "transcribe_audio_whisper.py")
transcribe_audio_whisper = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["transcribe_audio_whisper"] = transcribe_audio_whisper
SPEC.loader.exec_module(transcribe_audio_whisper)


class FakeModel:
    def transcribe(self, audio: str, *, language: str, fp16: bool) -> dict[str, object]:
        self.audio = audio
        self.language = language
        self.fp16 = fp16
        return {"text": "Testo trascritto.", "segments": [{"start": 0.0, "end": 1.0, "text": "Testo trascritto."}]}


class FakeWhisper:
    def __init__(self) -> None:
        self.model = FakeModel()
        self.calls: list[tuple[object, ...]] = []

    def load_model(self, model: str, *, device: str, download_root: str) -> FakeModel:
        self.calls.append((model, device, download_root))
        return self.model


class TranscribeAudioWhisperTests(unittest.TestCase):
    def test_openai_whisper_writes_compatible_raw_outputs_on_cpu(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "input" / "audio" / "sample.wav"
            audio.parent.mkdir(parents=True)
            audio.write_bytes(b"not-a-real-wave")
            model_cache = root / "cache" / "large-v3.pt"
            model_cache.parent.mkdir()
            model_cache.write_bytes(b"weights")
            whisper = FakeWhisper()

            with patch.object(transcribe_audio_whisper, "import_openai_whisper", return_value=whisper), patch(
                "whisper_runtime.local_model_path", return_value=model_cache
            ):
                success = transcribe_audio_whisper.transcribe_one(
                    root=root, audio_path=audio, model="large-v3", language="it", force=False
                )

            self.assertTrue(success)
            self.assertEqual(whisper.calls, [("large-v3", "cpu", str(model_cache.parent))])
            self.assertFalse(whisper.model.fp16)
            transcript = (root / "input" / "transcripts" / "raw" / "sample_raw.md").read_text(encoding="utf-8")
            report = json.loads((root / "output" / "transcription" / "sample_transcription.json").read_text(encoding="utf-8"))
            self.assertIn("transcription_engine: openai-whisper", transcript)
            self.assertEqual(report["transcription_engine"], "openai-whisper")
            self.assertEqual(report["transcription_model"], "large-v3")
            self.assertIn("quality_warnings", report)
            self.assertIn("normalization_candidates", report)
            self.assertIn("safe_for_analysis", report)
