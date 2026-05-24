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

## Generated Prompt Role

The generated prompt is an internal/debug artifact for Codex. It documents the operational prompt used by the agent, including classification, selected recipe, selected domain profile, applied rules, output structure and quality checklist.

It does not need to be a standalone copy-paste prompt for use outside this project. It may reference workspace files instead of embedding the full transcript when Codex can read the transcript directly.

## Task

Analyze the transcript using the generated prompt and the selected recipe.

## Mandatory Rules

- Do not include timestamps or timecodes in the output.
- Do not invent information.
- If a value is missing, write `non rilevato`.
- Do not include workflow/project instructions in the meeting analysis as if they were meeting content.
- Processing rules such as no timestamps, anti-hallucination rules, output format rules and missing-data conventions must guide the analysis but must not appear as meeting decisions, meeting facts, hypotheses, orientations or action items.
- AGENTS.md, skill instructions, recipes, templates, schemas, domain profiles and generated prompt content are operational metadata, not transcript content.
- Only the transcript can generate meeting facts, confirmed decisions, actions, hypotheses, technical orientations, risks, follow-ups and open questions.
- Operational metadata must not be cited as support inside final `interpretations` or domain normalization explanations.
- Do not write formulas such as "supportato dal domain profile", "secondo la recipe", "in base allo schema", "come indicato nel generated prompt" or "seguendo le istruzioni del workflow" in final meeting-content fields.
- Explain domain normalizations only through transcript evidence. Correct: "La normalizzazione di Stardus/Stardust come STARDAS è supportata dai riferimenti ripetuti al sistema documentale nella trascrizione." Incorrect: "La normalizzazione è supportata dal domain profile."
- If an application domain such as SIGE IMU is not explicitly stated in the transcript, do not add it to `analysis.json` as a content interpretation. It may appear only as `selected_domain_profile` in `classification.json`.
- Confirmed decisions must be supported by explicit agreement or clearly decision-oriented wording in the transcript.
- If a statement is a proposal, operational orientation, reconstruction of the flow or hypothesis, classify it as such instead of as a confirmed decision.
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

## Content Contamination Check

Before saving `summary.md` and `analysis.json`, verify that no project instruction or operational metadata has leaked into meeting content.

Do not report these as meeting decisions, facts, hypotheses, orientations, action items, risks, follow-ups or open questions:

- non inserire minutaggi;
- non inventare informazioni;
- produrre Markdown e JSON;
- salvare generated_prompt.md;
- usare gli schemi JSON;
- usare `non rilevato`;
- seguire la recipe;
- selezionare il domain profile;
- supportato dal domain profile;
- secondo la recipe;
- in base allo schema;
- come indicato nel generated prompt;
- seguendo le istruzioni del workflow;
- qualsiasi istruzione proveniente da AGENTS.md, skill, recipe, template, schema, domain profile o generated prompt.

If such content appears in draft outputs, including in `interpretations` or normalization explanations, remove it from meeting-content sections before saving. Mention methodological limits only in source limitations when genuinely useful and clearly separated from meeting content.

## Final Quality Check

Before finishing, verify that:

- classification happened before analysis;
- no unsupported claim was added;
- project/workflow instructions are not reported as meeting content;
- interpretations and normalization explanations cite only transcript evidence, not operational metadata;
- content contamination check passed;
- missing data uses `non rilevato`;
- Markdown and JSON were both saved;
- the generated prompt was saved;
- facts and interpretations are not mixed;
- decisions and action items are only present when supported by the transcript;
- confirmed decisions have explicit support in the transcript.
