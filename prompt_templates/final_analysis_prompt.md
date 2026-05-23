# Final Analysis Prompt Template

Use this template to apply the generated prompt to a transcript and produce final outputs.

## Context

- Transcript path: `{{transcript_path}}`
- Classification output path: `{{classification_output_path}}`
- Analysis JSON output path: `{{analysis_output_path}}`
- Markdown summary output path: `{{markdown_output_path}}`
- Generated prompt path: `{{generated_prompt_path}}`
- Selected recipe: `{{selected_recipe}}`
- Classification: `{{classification}}`

## Task

Analyze the transcript using the generated prompt and the selected recipe.

## Mandatory Rules

- Do not include timestamps or timecodes in the output.
- Do not invent information.
- If a value is missing, write `non rilevato`.
- Keep facts, interpretations, decisions, actions and open questions separate.
- Produce both Markdown and JSON.
- Save the generated prompt for debug before producing the final outputs.
- Follow the JSON schemas in `schemas/`.
- Keep the result concise, useful and traceable to the transcript.

## Required Markdown Output

Write `{{markdown_output_path}}` with these sections:

- `# Transcript Analysis`
- `## Classification`
- `## Summary`
- `## Key Points`
- `## Facts`
- `## Interpretations`
- `## Decisions`
- `## Action Items`
- `## Open Questions`
- `## Risks`
- `## Follow-ups`
- `## Source Limitations`

## Required JSON Outputs

Write `{{classification_output_path}}` following `schemas/classification.schema.json`.

Write `{{analysis_output_path}}` following `schemas/generic_analysis.schema.json` unless a more specific schema is added later.

## Final Quality Check

Before finishing, verify that:

- classification happened before analysis;
- no unsupported claim was added;
- missing data uses `non rilevato`;
- Markdown and JSON were both saved;
- the generated prompt was saved;
- facts and interpretations are not mixed;
- decisions and action items are only present when supported by the transcript.
