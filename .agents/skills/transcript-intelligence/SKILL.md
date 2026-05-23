# Transcript Intelligence Skill

Use this skill when working on transcript classification, recipe selection, structured extraction, or output quality control for this project.

## Rules

- Always classify the transcript before analysis.
- Do not invent facts that are not present in the transcript.
- Do not rely on unsupported assumptions. Mark inferred content as interpretation.
- Use `non rilevato` when information is absent or unclear.
- Always produce Markdown and JSON outputs.
- Keep facts, interpretations, decisions, actions and open questions separate.
- Prefer small, incremental changes without unapproved external dependencies.

## Expected Workflow

1. Read the transcript.
2. Lightly clean the transcript: remove obvious noise, normalize spacing and preserve meaning.
3. Classify the content type.
4. Select the most suitable recipe from `recipes/`.
5. Extract structured information according to the selected recipe.
6. Produce Markdown output for human review.
7. Produce JSON output for downstream automation.
8. Run a final quality check.

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

Generated prompts may be saved for debugging and reproducibility. The user should not need to manually rerun those prompts; the pipeline should own prompt construction and execution when implementation is added.

## Final Quality Check

- Confirm that classification happened before analysis.
- Confirm that unsupported claims are absent.
- Confirm that missing fields use `non rilevato`.
- Confirm that Markdown and JSON are both produced.
- Confirm that facts, interpretations, decisions, actions and open questions are separate.
