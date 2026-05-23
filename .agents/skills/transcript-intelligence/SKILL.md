# Transcript Intelligence Skill

Use this skill when Codex is asked to analyze a transcript in `input/transcripts/` with the agent-driven workflow. The skill covers classification, recipe selection, prompt generation, structured extraction, output writing and final quality control.

## Rules

- Always classify the transcript before analysis.
- Do not invent facts that are not present in the transcript.
- Do not rely on unsupported assumptions. Mark inferred content as interpretation.
- Use `non rilevato` when information is absent or unclear.
- Do not include timestamps, timecodes or minute markers in final outputs.
- Always produce Markdown and JSON outputs.
- Always save the generated prompt in `output/prompts/`.
- Keep facts, interpretations, decisions, actions and open questions separate.
- Prefer small, incremental changes without unapproved external dependencies.
- Do not create scripts, external API calls or new automation unless explicitly requested.

## Agent-Driven Workflow

1. Read `AGENTS.md`.
2. Read this skill file.
3. Read the requested transcript from `input/transcripts/`.
4. Lightly clean the transcript mentally: remove obvious noise, normalize spacing and preserve meaning.
5. Classify the content type.
6. Select the most suitable recipe from `recipes/`.
7. Read `prompt_templates/meta_prompt.md`.
8. Read `prompt_templates/final_analysis_prompt.md`.
9. Generate the optimized final prompt for the specific transcript.
10. Save it as `output/prompts/<name>_generated_prompt.md`.
11. Apply the generated prompt to the transcript.
12. Save Markdown output to `output/markdown/<name>_summary.md`.
13. Save JSON analysis to `output/json/<name>_analysis.json`.
14. Save JSON classification to `output/json/<name>_classification.json`.
15. Run a final quality check.

## Classification

Classification must include:

- `type`: primary content type.
- `confidence`: score from 0 to 1.
- `secondary_type`: alternate plausible type, or `non rilevato`.
- `signals`: textual clues that support the classification.
- `reason`: concise explanation.
- `recommended_recipe`: recipe file to use.

For ambiguous transcripts, lower the confidence score and fill `secondary_type`. If the transcript does not clearly match a known type, use `generic` and `recipes/generic.md`.

## Prompt Debugging

Generated prompts must be saved for debugging and reproducibility. The user should not need to manually rerun those prompts; Codex generates, saves and applies the prompt during the workflow.

For `input/transcripts/example.md`, expected debug prompt path:

- `output/prompts/example_generated_prompt.md`

## Final Quality Check

- Confirm that classification happened before analysis.
- Confirm that no timestamps or timecodes are included.
- Confirm that unsupported claims are absent.
- Confirm that missing fields use `non rilevato`.
- Confirm that Markdown and JSON are both produced.
- Confirm that the generated prompt is saved.
- Confirm that facts, interpretations, decisions, actions and open questions are separate.
