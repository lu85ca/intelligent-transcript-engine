from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WebinarPromptHardeningTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_webinar_recipe_contains_webinar_specific_sections(self) -> None:
        text = self.read("recipes/webinar.md")
        for expected in [
            "tools_mentioned",
            "demos_or_walkthroughs",
            "audience_questions",
            "detailed_summary",
            "takeaways",
            "applicable_actions",
        ]:
            self.assertIn(expected, text)

    def test_webinar_recipe_uses_single_primary_markdown(self) -> None:
        text = self.read("recipes/webinar.md")
        self.assertIn("unico deliverable Markdown", text)
        self.assertIn("Non generare `summary.md`", text)
        self.assertIn("legacy/stale", text)
        self.assertIn("output/markdown/<nome>_detailed_notes.md", text)

    def test_final_prompt_branches_for_webinar_outputs(self) -> None:
        text = self.read("prompt_templates/final_analysis_prompt.md")
        self.assertIn("recipes/webinar.md", text)
        self.assertIn("schemas/webinar_analysis.schema.json", text)
        self.assertIn("detailed_notes.md", text)
        self.assertIn("If `selected_recipe = recipes/generic.md`", text)

    def test_final_prompt_blocks_summary_for_long_webinars(self) -> None:
        text = self.read("prompt_templates/final_analysis_prompt.md")
        self.assertIn("write `detailed_notes.md` as the only Markdown deliverable", text)
        self.assertIn("Do not create, update or request `summary.md`", text)
        self.assertIn("legacy/stale", text)
        self.assertIn("For webinar long-form outputs, do not write `{{markdown_output_path}}`", text)

    def test_webinar_schema_exists_and_is_valid_json(self) -> None:
        path = ROOT / "schemas" / "webinar_analysis.schema.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["title"], "WebinarTranscriptAnalysis")

    def test_webinar_schema_contains_minimum_fields(self) -> None:
        data = json.loads((ROOT / "schemas" / "webinar_analysis.schema.json").read_text(encoding="utf-8"))
        required = set(data["required"])
        for field in {
            "executive_summary",
            "detailed_summary",
            "key_concepts",
            "tools_mentioned",
            "demos_or_walkthroughs",
            "audience_questions",
            "takeaways",
            "applicable_actions",
            "source_limitations",
        }:
            self.assertIn(field, required)

    def test_docs_mention_detailed_notes_for_long_webinars(self) -> None:
        combined = "\n".join(
            [
                self.read("README.md"),
                self.read("AGENTS.md"),
                self.read(".agents/skills/transcript-intelligence/SKILL.md"),
            ]
        )
        self.assertIn("detailed_notes.md", combined)
        self.assertIn("webinar_analysis.schema.json", combined)

    def test_docs_mark_detailed_notes_as_primary_webinar_markdown(self) -> None:
        for relative in [
            "README.md",
            "AGENTS.md",
            ".agents/skills/transcript-intelligence/SKILL.md",
        ]:
            text = self.read(relative)
            self.assertIn("detailed_notes.md", text)
            self.assertIn("summary.md", text)
            self.assertTrue(
                "unico Markdown" in text
                or "only Markdown" in text
                or "only primary Markdown" in text
                or "unico deliverable Markdown" in text
            )

    def test_scripts_do_not_invoke_codex_cli(self) -> None:
        for path in (ROOT / "scripts").glob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            self.assertNotIn("subprocess.run([\"codex\"", text)
            self.assertNotIn("subprocess.run(['codex'", text)
            self.assertNotIn("exec_command codex", text)

    def test_generic_recipe_remains_generic(self) -> None:
        text = self.read("recipes/generic.md")
        self.assertIn("# Generic Analysis Recipe", text)
        self.assertNotIn("demos_or_walkthroughs", text)
        self.assertNotIn("schemas/webinar_analysis.schema.json", text)

    def test_generic_analysis_schema_still_exists(self) -> None:
        path = ROOT / "schemas" / "generic_analysis.schema.json"
        self.assertTrue(path.exists())
        json.loads(path.read_text(encoding="utf-8"))

    def test_classification_schema_is_valid_json(self) -> None:
        path = ROOT / "schemas" / "classification.schema.json"
        self.assertTrue(path.exists())
        json.loads(path.read_text(encoding="utf-8"))

    def test_pdf_exporter_accepts_detailed_notes_path(self) -> None:
        text = self.read("scripts/export_summary_pdf.py")
        self.assertIn("_detailed_notes.md", text)
        self.assertIn("detailed_notes", text)


if __name__ == "__main__":
    unittest.main()
