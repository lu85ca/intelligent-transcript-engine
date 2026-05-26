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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


manage_candidates = load_module("manage_candidates", ROOT / "scripts" / "manage_candidates.py")
normalize_transcript = load_module("normalize_transcript_for_candidates", ROOT / "scripts" / "normalize_transcript.py")


class CandidateGlossaryTests(unittest.TestCase):
    def write_transcription_report(self, root: Path, basename: str, candidates: list[dict]) -> Path:
        path = root / "output" / "transcription" / f"{basename}_transcription.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"status": "ok", "normalization_candidates": candidates}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def write_reviewed(self, root: Path, basename: str, body: str) -> Path:
        path = root / "input" / "transcripts" / "reviewed" / f"{basename}_reviewed.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\nsource_type: reviewed_transcript\n---\n\n# Trascrizione revisionata\n\n" + body + "\n",
            encoding="utf-8",
        )
        return path

    def write_rules(self, root: Path, content: str = "rules: []\n") -> Path:
        path = root / "knowledge" / "work_meetings" / "normalization_rules.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            'version: 1\nscope: work_meetings\ndescription: "Test rules."\n' + content,
            encoding="utf-8",
        )
        return path

    def write_approved_terms(self, root: Path) -> Path:
        path = root / "knowledge" / "work_meetings" / "approved_terms.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            'version: 1\nscope: work_meetings\ndescription: "Test terms."\napproved_terms: []\n',
            encoding="utf-8",
        )
        return path

    def run_manage(self, root: Path, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = ["manage_candidates.py", *args]
        with patch.object(manage_candidates, "project_root", lambda: root), patch.object(
            manage_candidates.sys, "argv", argv
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            code = manage_candidates.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def run_normalize(self, root: Path, args: list[str]) -> tuple[int, str, str]:
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

    def test_collect_from_transcription_report_creates_candidate_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(
                root,
                "sample",
                [{"observed": "Copario Chat", "possible_canonical": "Copilot Chat", "confidence": "medium"}],
            )

            code, _, _ = self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])

            candidate_path = root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json"
            payload = json.loads(candidate_path.read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(payload["candidate_count"], 1)
            self.assertEqual(payload["candidates"][0]["status"], "candidate")
            self.assertEqual(payload["candidates"][0]["observed"], "Copario Chat")
            self.assertFalse((root / "knowledge" / "work_meetings" / "normalization_rules.yml").exists())

    def test_collect_without_candidates_creates_empty_candidate_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(root, "sample", [])

            code, _, _ = self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])

            payload = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(code, 0)
            self.assertEqual(payload["candidate_count"], 0)
            self.assertEqual(payload["candidates"], [])

    def test_collect_deduplicates_existing_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(
                root,
                "sample",
                [{"observed": "BLM", "possible_canonical": "LLM"}],
            )

            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])
            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])

            payload = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["candidate_count"], 1)
            self.assertEqual(payload["candidates"][0]["seen_in"], ["sample"])

    def test_same_observed_different_canonical_stays_separate_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(
                root,
                "sample",
                [
                    {"observed": "ABC", "possible_canonical": "Alpha"},
                    {"observed": "ABC", "possible_canonical": "Beta"},
                ],
            )

            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])

            payload = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["candidate_count"], 2)
            self.assertEqual(payload["warnings"][0]["type"], "candidate_conflict")

    def test_list_candidates_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(root, "sample", [{"observed": "BLM", "possible_canonical": "LLM"}])
            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])

            code, stdout, _ = self.run_manage(root, ["list", "--context", "work_meetings", "--json"])

            payload = json.loads(stdout)
            self.assertEqual(code, 0)
            self.assertEqual(payload["candidate_count"], 1)
            self.assertEqual(payload["candidates"][0]["observed"], "BLM")

    def test_promote_to_normalization_rules_updates_rule_and_status_without_duplication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(root, "sample", [{"observed": "BLM", "possible_canonical": "LLM"}])
            self.write_rules(root)
            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])
            payload = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            candidate_id = payload["candidates"][0]["id"]

            code, _, _ = self.run_manage(
                root,
                [
                    "promote",
                    "--context",
                    "work_meetings",
                    "--candidate-id",
                    candidate_id,
                    "--to",
                    "normalization_rules",
                ],
            )
            code_again, _, _ = self.run_manage(
                root,
                [
                    "promote",
                    "--context",
                    "work_meetings",
                    "--candidate-id",
                    candidate_id,
                    "--to",
                    "normalization_rules",
                ],
            )

            rules_text = (root / "knowledge" / "work_meetings" / "normalization_rules.yml").read_text(
                encoding="utf-8"
            )
            updated = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(code, 0)
            self.assertEqual(code_again, 0)
            self.assertEqual(rules_text.count('canonical: "LLM"'), 1)
            self.assertEqual(updated["candidates"][0]["status"], "promoted")
            self.assertTrue((root / "knowledge" / "work_meetings" / "candidates" / "promotion_log.jsonl").exists())

    def test_promote_conflict_fails_and_candidate_status_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(root, "sample", [{"observed": "BLM", "possible_canonical": "LLM"}])
            self.write_rules(
                root,
                """rules:
  - id: conflicting
    observed:
      - "BLM"
    canonical: "BPM"
    match: "word"
""",
            )
            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])
            payload = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            candidate_id = payload["candidates"][0]["id"]

            code, stdout, _ = self.run_manage(
                root,
                [
                    "promote",
                    "--context",
                    "work_meetings",
                    "--candidate-id",
                    candidate_id,
                    "--to",
                    "normalization_rules",
                    "--json",
                ],
            )

            updated = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(code, 1)
            self.assertIn("Conflicting normalization rule", stdout)
            self.assertEqual(updated["candidates"][0]["status"], "candidate")

    def test_promote_to_approved_terms_updates_term_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(
                root,
                "sample",
                [{"observed": "Copario Chat", "possible_canonical": "Copilot Chat"}],
            )
            self.write_approved_terms(root)
            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])
            payload = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            candidate_id = payload["candidates"][0]["id"]

            code, _, _ = self.run_manage(
                root,
                ["promote", "--context", "work_meetings", "--candidate-id", candidate_id, "--to", "approved_terms"],
            )

            terms_text = (root / "knowledge" / "work_meetings" / "approved_terms.yml").read_text(encoding="utf-8")
            updated = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(code, 0)
            self.assertIn('canonical: "Copilot Chat"', terms_text)
            self.assertEqual(updated["candidates"][0]["status"], "promoted")

    def test_reject_candidate_does_not_modify_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(root, "sample", [{"observed": "BLM", "possible_canonical": "LLM"}])
            rules = self.write_rules(root)
            before = rules.read_text(encoding="utf-8")
            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])
            payload = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            candidate_id = payload["candidates"][0]["id"]

            code, _, _ = self.run_manage(
                root,
                ["reject", "--context", "work_meetings", "--candidate-id", candidate_id, "--notes", "invalid"],
            )

            updated = json.loads(
                (root / "knowledge" / "work_meetings" / "candidates" / "sample_candidates.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(code, 0)
            self.assertEqual(rules.read_text(encoding="utf-8"), before)
            self.assertEqual(updated["candidates"][0]["status"], "rejected")

    def test_step3_does_not_apply_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_reviewed(root, "sample", "Uso Copario Chat.")
            self.write_rules(root)
            candidate_dir = root / "knowledge" / "work_meetings" / "candidates"
            candidate_dir.mkdir(parents=True, exist_ok=True)
            (candidate_dir / "sample_candidates.json").write_text(
                json.dumps(
                    {
                        "basename": "sample",
                        "context": "work_meetings",
                        "candidate_count": 1,
                        "candidates": [
                            {
                                "id": "cand_test",
                                "observed": "Copario Chat",
                                "possible_canonical": "Copilot Chat",
                                "status": "candidate",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            code, _, _ = self.run_normalize(root, ["sample", "--context", "work_meetings"])

            normalized = (root / "input" / "transcripts" / "normalized" / "sample_normalized.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(code, 0)
            self.assertIn("Copario Chat", normalized)
            self.assertNotIn("Copilot Chat", normalized)

    def test_candidate_commands_do_not_create_agent_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_transcription_report(root, "sample", [{"observed": "BLM", "possible_canonical": "LLM"}])
            self.run_manage(root, ["collect", "sample", "--context", "work_meetings"])
            self.run_manage(root, ["list", "--context", "work_meetings"])

            self.assertFalse((root / "output" / "markdown").exists())
            self.assertFalse((root / "output" / "json").exists())
            self.assertFalse((root / "output" / "prompts").exists())


if __name__ == "__main__":
    unittest.main()
