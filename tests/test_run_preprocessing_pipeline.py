from __future__ import annotations

import argparse
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_preprocessing_pipeline",
    ROOT / "scripts" / "run_preprocessing_pipeline.py",
)
run_preprocessing_pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["run_preprocessing_pipeline"] = run_preprocessing_pipeline
SPEC.loader.exec_module(run_preprocessing_pipeline)


class FakeRunner:
    def __init__(self, root: Path, basename: str, selector_requires_review: bool = False) -> None:
        self.root = root
        self.basename = basename
        self.selector_requires_review = selector_requires_review
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], *, root: Path, verbose: bool) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        joined = " ".join(command)
        if "process_videos.sh" in joined or "transcribe_audio_mlx.py" in joined:
            self.write_raw()
            return subprocess.CompletedProcess(command, 0, stdout="raw ok\n", stderr="")
        if "prepare_review_transcript.py" in joined:
            self.write_reviewed()
            return subprocess.CompletedProcess(command, 0, stdout="review ok\n", stderr="")
        if "normalize_transcript.py" in joined:
            self.write_normalized()
            return subprocess.CompletedProcess(command, 0, stdout="normalization ok\n", stderr="")
        if "manage_candidates.py" in joined and " collect " in f" {joined} ":
            payload = {"candidate_count": 2, "candidate_file": f"knowledge/work_meetings/candidates/{self.basename}_candidates.json"}
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")
        if "select_analysis_transcript.py" in joined:
            if self.selector_requires_review:
                payload = {
                    "basename": self.basename,
                    "selected_transcript": None,
                    "selected_level": None,
                    "decision": "requires_review",
                    "safe_for_analysis": False,
                    "requires_review": True,
                    "reason": "Only raw transcript exists and technical report marks it as not safe for analysis.",
                    "checked_paths": {},
                }
                return subprocess.CompletedProcess(command, 1, stdout=json.dumps(payload), stderr="")
            selected = f"input/transcripts/normalized/{self.basename}_normalized.md"
            payload = {
                "basename": self.basename,
                "selected_transcript": selected,
                "selected_level": "normalized",
                "decision": "selected_normalized",
                "safe_for_analysis": False,
                "requires_review": False,
                "reason": "Normalized transcript exists and has priority over reviewed/raw.",
                "checked_paths": {},
            }
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")
        return subprocess.CompletedProcess(command, 99, stdout="", stderr="unexpected command")

    def write_raw(self) -> None:
        path = self.root / "input" / "transcripts" / "raw" / f"{self.basename}_raw.md"
        report = self.root / "output" / "transcription" / f"{self.basename}_transcription.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        report.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("raw\n", encoding="utf-8")
        report.write_text('{"safe_for_analysis": true}\n', encoding="utf-8")

    def write_reviewed(self) -> None:
        path = self.root / "input" / "transcripts" / "reviewed" / f"{self.basename}_reviewed.md"
        report = self.root / "output" / "review" / f"{self.basename}_review.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        report.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("reviewed\n", encoding="utf-8")
        report.write_text('{"status": "ok"}\n', encoding="utf-8")

    def write_normalized(self) -> None:
        path = self.root / "input" / "transcripts" / "normalized" / f"{self.basename}_normalized.md"
        report = self.root / "output" / "normalization" / f"{self.basename}_normalization.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        report.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("normalized\n", encoding="utf-8")
        report.write_text('{"status": "ok"}\n', encoding="utf-8")


class RunPreprocessingPipelineTests(unittest.TestCase):
    def args(self, input_value: str | None = "sample", **overrides) -> argparse.Namespace:
        values = {
            "input": input_value,
            "latest_video": False,
            "context": "work_meetings",
            "force": False,
            "apply_safe_cleanup": False,
            "dry_run": False,
            "json": False,
            "verbose": False,
            "skip_transcription": False,
            "skip_candidates": False,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def write_all_outputs(self, root: Path, basename: str = "sample") -> None:
        fake = FakeRunner(root, basename)
        fake.write_raw()
        fake.write_reviewed()
        fake.write_normalized()

    def test_dry_run_from_basename_does_not_execute_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeRunner(root, "sample")
            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(
                    self.args("sample", dry_run=True),
                    root,
                )

            self.assertEqual(code, 0)
            self.assertEqual(fake.commands, [])
            self.assertEqual(report["pipeline_status"], "dry_run")
            self.assertEqual([step["name"] for step in report["steps"]], [
                "transcription",
                "review",
                "normalization",
                "candidate_collection",
                "transcript_selection",
            ])
            self.assertFalse((root / "output" / "pipeline").exists())

    def test_existing_outputs_are_skipped_and_report_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_all_outputs(root)
            fake = FakeRunner(root, "sample")

            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(self.args("sample"), root)

            statuses = {step["name"]: step["status"] for step in report["steps"]}
            self.assertEqual(code, 0)
            self.assertEqual(statuses["transcription"], "skipped_existing_output")
            self.assertEqual(statuses["review"], "skipped_existing_output")
            self.assertEqual(statuses["normalization"], "skipped_existing_output")
            self.assertEqual(report["pipeline_status"], "ready_for_agent_analysis")
            self.assertEqual(report["candidate_count"], 2)
            self.assertTrue((root / "output" / "pipeline" / "sample_pipeline.json").exists())
            self.assertFalse(any("codex" in " ".join(command).lower() for command in fake.commands))

    def test_missing_reviewed_triggers_review_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeRunner(root, "sample")
            fake.write_raw()

            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(self.args("sample"), root)

            self.assertEqual(code, 0)
            self.assertIn("prepare_review_transcript.py", " ".join(" ".join(command) for command in fake.commands))
            self.assertEqual(next(step for step in report["steps"] if step["name"] == "review")["status"], "completed")

    def test_missing_normalized_triggers_normalization_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeRunner(root, "sample")
            fake.write_raw()
            fake.write_reviewed()

            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(self.args("sample"), root)

            self.assertEqual(code, 0)
            self.assertIn("normalize_transcript.py", " ".join(" ".join(command) for command in fake.commands))
            self.assertEqual(next(step for step in report["steps"] if step["name"] == "normalization")["status"], "completed")

    def test_candidate_collection_invoked_without_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_all_outputs(root)
            fake = FakeRunner(root, "sample")

            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(self.args("sample"), root)

            joined = "\n".join(" ".join(command) for command in fake.commands)
            self.assertEqual(code, 0)
            self.assertIn("manage_candidates.py collect", joined)
            self.assertNotIn("promote", joined)
            self.assertEqual(next(step for step in report["steps"] if step["name"] == "candidate_collection")["candidate_count"], 2)

    def test_selector_ready_sets_ready_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_all_outputs(root)
            fake = FakeRunner(root, "sample")

            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(self.args("sample"), root)

            self.assertEqual(code, 0)
            self.assertTrue(report["ready_for_agent_analysis"])
            self.assertEqual(report["selected_level"], "normalized")
            self.assertEqual(report["selection_decision"], "selected_normalized")

    def test_selector_requires_review_blocks_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_all_outputs(root)
            fake = FakeRunner(root, "sample", selector_requires_review=True)

            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(self.args("sample"), root)

            self.assertEqual(code, 1)
            self.assertEqual(report["pipeline_status"], "requires_manual_review")
            self.assertFalse(report["ready_for_agent_analysis"])
            self.assertIsNone(report["selected_transcript"])

    def test_report_contains_minimum_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_all_outputs(root)
            fake = FakeRunner(root, "sample")

            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, _ = run_preprocessing_pipeline.run_preprocessing_pipeline(self.args("sample"), root)

            for field in {
                "basename",
                "context",
                "pipeline_status",
                "ready_for_agent_analysis",
                "selected_transcript",
                "selected_level",
                "steps",
                "reports",
                "next_action",
                "created_at",
            }:
                self.assertIn(field, report)

    def test_latest_video_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video_dir = root / "input" / "videos"
            video_dir.mkdir(parents=True)
            old = video_dir / "old.mp4"
            new = video_dir / "new.mkv"
            old.write_text("old", encoding="utf-8")
            new.write_text("new", encoding="utf-8")
            old.touch()
            new.touch()

            report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(
                self.args(None, latest_video=True, dry_run=True),
                root,
            )

            self.assertEqual(code, 0)
            self.assertEqual(report["basename"], "new")
            self.assertEqual(report["input"]["source_video"], "input/videos/new.mkv")

    def test_json_stdout_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_all_outputs(root)
            fake = FakeRunner(root, "sample")
            stdout = io.StringIO()
            stderr = io.StringIO()
            argv = ["run_preprocessing_pipeline.py", "sample", "--json"]

            with patch.object(run_preprocessing_pipeline, "project_root", lambda: root), patch.object(
                run_preprocessing_pipeline, "run_command", fake
            ), patch.object(run_preprocessing_pipeline.sys, "argv", argv), redirect_stdout(stdout), redirect_stderr(stderr):
                code = run_preprocessing_pipeline.main()

            self.assertEqual(code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(json.loads(stdout.getvalue())["pipeline_status"], "ready_for_agent_analysis")

    def test_runner_does_not_create_agent_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_all_outputs(root)
            fake = FakeRunner(root, "sample")

            with patch.object(run_preprocessing_pipeline, "run_command", fake):
                report, code = run_preprocessing_pipeline.run_preprocessing_pipeline(self.args("sample"), root)

            self.assertEqual(code, 0)
            self.assertEqual(report["pipeline_status"], "ready_for_agent_analysis")
            self.assertFalse((root / "output" / "markdown").exists())
            self.assertFalse((root / "output" / "json").exists())
            self.assertFalse((root / "output" / "prompts").exists())


if __name__ == "__main__":
    unittest.main()
