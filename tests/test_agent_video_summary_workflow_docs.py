from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentVideoSummaryWorkflowDocsTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_agents_mentions_step6a_and_selected_transcript(self) -> None:
        text = self.read("AGENTS.md")

        self.assertIn("scripts/run_preprocessing_pipeline.py", text)
        self.assertIn("ready_for_agent_analysis", text)
        self.assertIn("selected_transcript", text)
        self.assertIn("fermarsi", text)
        self.assertIn("solo la trascrizione selezionata", text)

    def test_skill_handles_video_summary_requests(self) -> None:
        text = self.read(".agents/skills/transcript-intelligence/SKILL.md")

        self.assertIn("riassumi questo video", text)
        self.assertIn("scripts/run_preprocessing_pipeline.py", text)
        self.assertIn("ready_for_agent_analysis: false", text)
        self.assertIn("selected_transcript", text)
        self.assertIn("candidate_count", text)

    def test_skill_keeps_technical_metadata_out_of_content(self) -> None:
        text = self.read(".agents/skills/transcript-intelligence/SKILL.md")

        for phrase in [
            "Pipeline reports",
            "quality warnings",
            "normalization candidates",
            "technical logs",
            "operational metadata",
        ]:
            self.assertIn(phrase, text)

    def test_readme_documents_one_prompt_video_flow(self) -> None:
        text = self.read("README.md")

        self.assertIn("Riassumere un video con Codex", text)
        self.assertIn("scripts/run_preprocessing_pipeline.py --latest-video", text)
        self.assertIn("ready_for_agent_analysis", text)
        self.assertIn("output/prompts/<nome>_generated_prompt.md", text)
        self.assertIn("output/markdown/<nome>_summary.md", text)
        self.assertIn("output/json/<nome>_classification.json", text)
        self.assertIn("output/json/<nome>_analysis.json", text)

    def test_scripts_do_not_invoke_codex_cli(self) -> None:
        forbidden_patterns = [
            re.compile(r"subprocess\.(?:run|Popen|call|check_call|check_output)\([^)]*codex", re.IGNORECASE | re.DOTALL),
            re.compile(r"os\.system\([^)]*codex", re.IGNORECASE | re.DOTALL),
            re.compile(r"\bcodex\s+\""),
        ]

        for path in (ROOT / "scripts").glob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertIsNone(pattern.search(text), f"Codex CLI invocation found in {path}")

    def test_candidate_promotion_remains_manual(self) -> None:
        agents = self.read("AGENTS.md")
        skill = self.read(".agents/skills/transcript-intelligence/SKILL.md")
        readme = self.read("README.md")
        combined = "\n".join([agents, skill, readme])

        self.assertIn("non vengono promossi automaticamente", combined)
        self.assertIn("Do not apply candidates unless they have been manually promoted", skill)
        self.assertIn("non promuove nulla automaticamente", readme)


if __name__ == "__main__":
    unittest.main()
