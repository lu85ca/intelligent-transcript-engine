from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "select_analysis_transcript",
    ROOT / "scripts" / "select_analysis_transcript.py",
)
select_analysis_transcript = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["select_analysis_transcript"] = select_analysis_transcript
SPEC.loader.exec_module(select_analysis_transcript)


class SelectAnalysisTranscriptTests(unittest.TestCase):
    def write_transcript(self, root: Path, level: str, basename: str, body: str = "Test") -> Path:
        suffixes = {
            "raw": "_raw.md",
            "reviewed": "_reviewed.md",
            "normalized": "_normalized.md",
        }
        path = root / "input" / "transcripts" / level / f"{basename}{suffixes[level]}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nsource_type: {level}\n---\n\n{body}\n", encoding="utf-8")
        return path

    def write_report(self, root: Path, basename: str, safe_for_analysis: bool | None) -> Path:
        path = root / "output" / "transcription" / f"{basename}_transcription.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "ok",
                    "safe_for_analysis": safe_for_analysis,
                    "quality_warnings": [{"type": "possible_intro_loop"}],
                    "normalization_candidates": [{"observed": "BLM"}],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def run_cli(self, root: Path, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = ["select_analysis_transcript.py", *args]
        with patch.object(select_analysis_transcript, "project_root", lambda: root), patch.object(
            select_analysis_transcript.sys, "argv", argv
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            code = select_analysis_transcript.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_normalized_exists_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcript(root, "raw", "sample")
            self.write_transcript(root, "reviewed", "sample")
            normalized = self.write_transcript(root, "normalized", "sample")
            self.write_report(root, "sample", False)

            decision, code = select_analysis_transcript.select_transcript(input_value="sample", root=root)

            self.assertEqual(code, 0)
            self.assertEqual(decision["selected_transcript"], normalized.relative_to(root).as_posix())
            self.assertEqual(decision["selected_level"], "normalized")
            self.assertEqual(decision["decision"], "selected_normalized")
            self.assertFalse(decision["requires_review"])

    def test_reviewed_selected_when_normalized_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcript(root, "raw", "sample")
            reviewed = self.write_transcript(root, "reviewed", "sample")
            self.write_report(root, "sample", False)

            decision, code = select_analysis_transcript.select_transcript(input_value="sample", root=root)

            self.assertEqual(code, 0)
            self.assertEqual(decision["selected_transcript"], reviewed.relative_to(root).as_posix())
            self.assertEqual(decision["selected_level"], "reviewed")
            self.assertEqual(decision["decision"], "selected_reviewed")

    def test_only_raw_safe_for_analysis_true_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = self.write_transcript(root, "raw", "sample")
            self.write_report(root, "sample", True)

            decision, code = select_analysis_transcript.select_transcript(input_value="sample", root=root)

            self.assertEqual(code, 0)
            self.assertEqual(decision["selected_transcript"], raw.relative_to(root).as_posix())
            self.assertEqual(decision["selected_level"], "raw")
            self.assertEqual(decision["safe_for_analysis"], True)

    def test_only_raw_safe_for_analysis_false_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcript(root, "raw", "sample")
            self.write_report(root, "sample", False)

            decision, code = select_analysis_transcript.select_transcript(input_value="sample", root=root)

            self.assertEqual(code, 1)
            self.assertIsNone(decision["selected_transcript"])
            self.assertTrue(decision["requires_review"])
            self.assertEqual(decision["decision"], "requires_review")
            self.assertEqual(decision["safe_for_analysis"], False)
            self.assertEqual(decision["quality_warnings"], [{"type": "possible_intro_loop"}])

    def test_only_raw_safe_for_analysis_null_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcript(root, "raw", "sample")
            self.write_report(root, "sample", None)

            decision, code = select_analysis_transcript.select_transcript(input_value="sample", root=root)

            self.assertEqual(code, 1)
            self.assertIsNone(decision["selected_transcript"])
            self.assertTrue(decision["requires_review"])
            self.assertIsNone(decision["safe_for_analysis"])

    def test_only_raw_missing_technical_report_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcript(root, "raw", "sample")

            decision, code = select_analysis_transcript.select_transcript(input_value="sample", root=root)

            self.assertEqual(code, 1)
            self.assertIsNone(decision["selected_transcript"])
            self.assertTrue(decision["requires_review"])
            self.assertIn("missing", decision["reason"])

    def test_no_transcript_exists_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            decision, code = select_analysis_transcript.select_transcript(input_value="missing", root=root)

            self.assertEqual(code, 1)
            self.assertEqual(decision["decision"], "missing_transcript")
            self.assertTrue(decision["requires_review"])

    def test_input_as_path_derives_basename_and_applies_full_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviewed = self.write_transcript(root, "reviewed", "sample")
            normalized = self.write_transcript(root, "normalized", "sample")

            decision, code = select_analysis_transcript.select_transcript(input_value=reviewed.as_posix(), root=root)

            self.assertEqual(code, 0)
            self.assertEqual(decision["selected_transcript"], normalized.relative_to(root).as_posix())
            self.assertEqual(decision["selected_level"], "normalized")

    def test_json_output_contains_minimum_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcript(root, "raw", "sample")
            self.write_report(root, "sample", True)

            code, stdout, _ = self.run_cli(root, ["sample", "--json"])
            decision = json.loads(stdout)

            self.assertEqual(code, 0)
            for field in {
                "basename",
                "selected_transcript",
                "selected_level",
                "decision",
                "safe_for_analysis",
                "requires_review",
                "reason",
                "checked_paths",
            }:
                self.assertIn(field, decision)

    def test_selector_does_not_modify_inputs_or_create_analysis_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = self.write_transcript(root, "raw", "sample", body="Original raw")
            report = self.write_report(root, "sample", True)
            raw_before = raw.read_text(encoding="utf-8")
            report_before = report.read_text(encoding="utf-8")

            code, stdout, _ = self.run_cli(root, ["sample"])

            self.assertEqual(code, 0)
            self.assertIn("input/transcripts/raw/sample_raw.md", stdout)
            self.assertEqual(raw.read_text(encoding="utf-8"), raw_before)
            self.assertEqual(report.read_text(encoding="utf-8"), report_before)
            self.assertFalse((root / "output" / "markdown").exists())
            self.assertFalse((root / "output" / "json").exists())
            self.assertFalse((root / "output" / "prompts").exists())

    def test_allow_unsafe_raw_is_explicit_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = self.write_transcript(root, "raw", "sample")
            self.write_report(root, "sample", False)

            decision, code = select_analysis_transcript.select_transcript(
                input_value="sample",
                root=root,
                allow_unsafe_raw=True,
            )

            self.assertEqual(code, 0)
            self.assertEqual(decision["selected_transcript"], raw.relative_to(root).as_posix())
            self.assertEqual(decision["decision"], "selected_raw_unsafe_override")
            self.assertTrue(decision["unsafe_override"])


if __name__ == "__main__":
    unittest.main()
