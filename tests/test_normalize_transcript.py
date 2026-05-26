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
    "normalize_transcript",
    ROOT / "scripts" / "normalize_transcript.py",
)
normalize_transcript = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["normalize_transcript"] = normalize_transcript
SPEC.loader.exec_module(normalize_transcript)


class NormalizeTranscriptTests(unittest.TestCase):
    def write_reviewed(self, root: Path, basename: str, body: str, frontmatter_extra: str = "") -> Path:
        path = root / "input" / "transcripts" / "reviewed" / f"{basename}_reviewed.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            "source_type: reviewed_transcript\n"
            f"{frontmatter_extra}"
            "---\n\n"
            "# Trascrizione revisionata\n\n"
            f"{body}\n",
            encoding="utf-8",
        )
        return path

    def write_rules(self, root: Path, relative_dir: str, content: str) -> Path:
        path = root / relative_dir / "normalization_rules.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_cli(self, root: Path, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = ["normalize_transcript.py", *args]
        with patch.object(normalize_transcript.Path, "resolve", lambda self: self), patch.object(
            normalize_transcript.sys, "argv", argv
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            with patch.object(
                normalize_transcript.Path,
                "parents",
                new_callable=lambda: property(lambda _self: [root / "scripts", root]),
            ):
                code = normalize_transcript.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_loads_rules_and_applies_word_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules_path = root / "knowledge" / "global" / "normalization_rules.yml"
            rules_path.parent.mkdir(parents=True)
            rules_path.write_text(
                """rules:
  - id: llm_from_blm
    enabled: true
    observed:
      - "BLM"
    canonical: "LLM"
    match: "word"
    case_sensitive: false
""",
                encoding="utf-8",
            )
            context_path = root / "knowledge" / "work_meetings" / "normalization_rules.yml"
            context_path.parent.mkdir(parents=True)
            context_path.write_text("rules: []\n", encoding="utf-8")

            rules, _, skipped = normalize_transcript.load_rules(root, "work_meetings")
            conflicts, _ = normalize_transcript.find_conflicts(rules)
            candidates = normalize_transcript.build_candidates(rules, conflicts)
            normalized, replacements, warnings = normalize_transcript.apply_rules(
                "Un BLM non e' un BLMx.",
                candidates,
            )

        self.assertEqual(skipped, [])
        self.assertEqual(warnings, [])
        self.assertEqual(normalized, "Un LLM non e' un BLMx.")
        self.assertEqual(replacements[0]["count"], 1)

    def test_conflicting_rules_are_not_applied(self) -> None:
        rule_a = normalize_transcript.Rule(
            id="a",
            observed=("BLM",),
            canonical="LLM",
            match="word",
            case_sensitive=False,
            enabled=True,
            source="test",
        )
        rule_b = normalize_transcript.Rule(
            id="b",
            observed=("BLM",),
            canonical="BPM",
            match="word",
            case_sensitive=False,
            enabled=True,
            source="test",
        )

        conflict_ids, conflicts = normalize_transcript.find_conflicts([rule_a, rule_b])
        candidates = normalize_transcript.build_candidates([rule_a, rule_b], conflict_ids)
        normalized, replacements, _ = normalize_transcript.apply_rules("BLM", candidates)

        self.assertEqual(normalized, "BLM")
        self.assertEqual(replacements, [])
        self.assertEqual(conflict_ids, {"a", "b"})
        self.assertEqual(len(conflicts), 1)

    def test_phrase_prevents_overlapping_word_replacement(self) -> None:
        phrase_rule = normalize_transcript.Rule(
            id="copilot_chat",
            observed=("Copario Chat",),
            canonical="Copilot Chat",
            match="phrase",
            case_sensitive=False,
            enabled=True,
            source="test",
        )
        word_rule = normalize_transcript.Rule(
            id="chat",
            observed=("Chat",),
            canonical="CHAT",
            match="word",
            case_sensitive=False,
            enabled=True,
            source="test",
        )
        candidates = normalize_transcript.build_candidates([phrase_rule, word_rule], set())
        normalized, replacements, warnings = normalize_transcript.apply_rules("Copario Chat", candidates)

        self.assertEqual(normalized, "Copilot Chat")
        self.assertEqual(replacements[0]["rule_id"], "copilot_chat")
        self.assertEqual(len(warnings), 1)

    def test_missing_reviewed_transcript_fails_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _, stderr = self.run_cli(root, ["missing", "--context", "work_meetings"])

            self.assertEqual(code, 1)
            self.assertIn("Reviewed transcript not found", stderr)
            self.assertFalse((root / "input" / "transcripts" / "normalized").exists())
            self.assertFalse((root / "output" / "normalization").exists())

    def test_no_rules_creates_identical_normalized_body_and_zero_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "BLM resta BLM.")
            self.write_rules(root, "knowledge/global", "rules: []\n")
            self.write_rules(root, "knowledge/work_meetings", "rules: []\n")

            code, _, _ = self.run_cli(root, ["sample", "--context", "work_meetings"])

            normalized = (root / "input" / "transcripts" / "normalized" / "sample_normalized.md").read_text(
                encoding="utf-8"
            )
            report = json.loads(
                (root / "output" / "normalization" / "sample_normalization.json").read_text(encoding="utf-8")
            )
            self.assertEqual(code, 0)
            self.assertIn("BLM resta BLM.", normalized)
            self.assertEqual(report["rules_loaded"], 0)
            self.assertEqual(report["rules_enabled"], 0)
            self.assertEqual(report["rules_applied"], 0)
            self.assertEqual(report["total_replacements"], 0)
            self.assertFalse(report["normalization_performed"])

    def test_dry_run_does_not_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "BLM")
            self.write_rules(root, "knowledge/global", "rules: []\n")
            self.write_rules(root, "knowledge/work_meetings", "rules: []\n")

            code, stdout, _ = self.run_cli(root, ["sample", "--context", "work_meetings", "--dry-run"])

            self.assertEqual(code, 0)
            self.assertIn("Dry run", stdout)
            self.assertIn('"basename": "sample"', stdout)
            self.assertFalse((root / "input" / "transcripts" / "normalized" / "sample_normalized.md").exists())
            self.assertFalse((root / "output" / "normalization" / "sample_normalization.json").exists())

    def test_existing_outputs_without_force_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "BLM")
            normalized = root / "input" / "transcripts" / "normalized" / "sample_normalized.md"
            report = root / "output" / "normalization" / "sample_normalization.json"
            normalized.parent.mkdir(parents=True)
            report.parent.mkdir(parents=True)
            normalized.write_text("KEEP", encoding="utf-8")
            report.write_text('{"keep": true}\n', encoding="utf-8")

            code, stdout, _ = self.run_cli(root, ["sample", "--context", "work_meetings"])

            self.assertEqual(code, 0)
            self.assertIn("already exist", stdout)
            self.assertEqual(normalized.read_text(encoding="utf-8"), "KEEP")
            self.assertEqual(report.read_text(encoding="utf-8"), '{"keep": true}\n')

    def test_existing_outputs_with_force_are_regenerated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "BLM")
            self.write_rules(
                root,
                "knowledge/global",
                """rules:
  - id: llm
    observed:
      - "BLM"
    canonical: "LLM"
    match: "word"
""",
            )
            self.write_rules(root, "knowledge/work_meetings", "rules: []\n")
            normalized = root / "input" / "transcripts" / "normalized" / "sample_normalized.md"
            report = root / "output" / "normalization" / "sample_normalization.json"
            normalized.parent.mkdir(parents=True)
            report.parent.mkdir(parents=True)
            normalized.write_text("OLD", encoding="utf-8")
            report.write_text('{"old": true}\n', encoding="utf-8")

            code, _, _ = self.run_cli(root, ["sample", "--context", "work_meetings", "--force"])

            self.assertEqual(code, 0)
            self.assertIn("LLM", normalized.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["total_replacements"], 1)

    def test_candidates_are_not_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "Uso Copario Chat.")
            self.write_rules(root, "knowledge/global", "rules: []\n")
            self.write_rules(root, "knowledge/work_meetings", "rules: []\n")
            candidate = root / "knowledge" / "work_meetings" / "candidates" / "candidate.yml"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("observed: Copario Chat\npossible_canonical: Copilot Chat\n", encoding="utf-8")

            code, _, _ = self.run_cli(root, ["sample", "--context", "work_meetings"])

            normalized = (root / "input" / "transcripts" / "normalized" / "sample_normalized.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(code, 0)
            self.assertIn("Copario Chat", normalized)
            self.assertNotIn("Copilot Chat", normalized)

    def test_input_via_reviewed_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviewed = self.write_reviewed(root, "sample", "Test")
            self.write_rules(root, "knowledge/global", "rules: []\n")
            self.write_rules(root, "knowledge/work_meetings", "rules: []\n")

            code, _, _ = self.run_cli(root, [reviewed.as_posix(), "--context", "work_meetings"])

            self.assertEqual(code, 0)
            self.assertTrue((root / "input" / "transcripts" / "normalized" / "sample_normalized.md").exists())

    def test_report_contains_minimum_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "Test")
            self.write_rules(root, "knowledge/global", "rules: []\n")
            self.write_rules(root, "knowledge/work_meetings", "rules: []\n")

            self.run_cli(root, ["sample", "--context", "work_meetings"])
            report = json.loads(
                (root / "output" / "normalization" / "sample_normalization.json").read_text(encoding="utf-8")
            )

            for field in {
                "basename",
                "source_transcript",
                "normalized_transcript",
                "normalization_context",
                "knowledge_sources",
                "normalization_performed",
                "rules_loaded",
                "rules_enabled",
                "rules_applied",
                "total_replacements",
                "replacements",
                "conflicts",
                "skipped_rules",
                "warnings",
                "created_at",
            }:
                self.assertIn(field, report)

    def test_cli_end_to_end_with_two_approved_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "BLM e Copario Chat. BLMx resta.")
            self.write_rules(
                root,
                "knowledge/global",
                """rules:
  - id: llm_from_blm
    observed:
      - "BLM"
    canonical: "LLM"
    match: "word"
  - id: copilot_chat_from_copario_chat
    observed:
      - "Copario Chat"
    canonical: "Copilot Chat"
    match: "phrase"
""",
            )
            self.write_rules(root, "knowledge/work_meetings", "rules: []\n")

            code, _, _ = self.run_cli(root, ["sample", "--context", "work_meetings"])

            normalized = (root / "input" / "transcripts" / "normalized" / "sample_normalized.md").read_text(
                encoding="utf-8"
            )
            report = json.loads(
                (root / "output" / "normalization" / "sample_normalization.json").read_text(encoding="utf-8")
            )
            self.assertEqual(code, 0)
            self.assertIn("LLM e Copilot Chat. BLMx resta.", normalized)
            self.assertEqual(report["total_replacements"], 2)
            counts = {item["rule_id"]: item["count"] for item in report["replacements"]}
            self.assertEqual(counts["llm_from_blm"], 1)
            self.assertEqual(counts["copilot_chat_from_copario_chat"], 1)

    def test_frontmatter_is_not_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "Nel body BLM.", frontmatter_extra="source_note: BLM\n")
            self.write_rules(
                root,
                "knowledge/global",
                """rules:
  - id: llm
    observed:
      - "BLM"
    canonical: "LLM"
    match: "word"
""",
            )
            self.write_rules(root, "knowledge/work_meetings", "rules: []\n")

            self.run_cli(root, ["sample", "--context", "work_meetings"])
            normalized = (root / "input" / "transcripts" / "normalized" / "sample_normalized.md").read_text(
                encoding="utf-8"
            )

            self.assertNotIn("source_note: LLM", normalized)
            self.assertIn("Nel body LLM.", normalized)


if __name__ == "__main__":
    unittest.main()
