# Final Analysis Prompt Template

Use this template to apply the generated prompt to a transcript and produce final outputs.

## Context

- Transcript path: `{{transcript_path}}`
- Classification output path: `{{classification_output_path}}`
- Analysis JSON output path: `{{analysis_output_path}}`
- Markdown summary output path: `{{markdown_output_path}}`
- Detailed notes output path: `{{detailed_notes_output_path}}`
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
- Keep the result useful and traceable to the transcript.
- For webinar/round_table long-form content, write `detailed_notes.md` as the only Markdown deliverable. Do not create, update or request `summary.md` for this recipe. If `summary.md` already exists from a previous run, treat it as legacy/stale and do not update it.

## Required Markdown Output

If `selected_recipe = recipes/webinar.md` or `type = webinar` and the transcript is long-form webinar/round table content, write only `{{detailed_notes_output_path}}` with webinar-specific sections:

- `# Webinar Detailed Notes`
- `## Classification`
- `## Executive Overview`
- `## Content Map`
- `## Detailed Thematic Sections`
- `## Key Concepts`
- `## Tools, Platforms And Assets Mentioned`
- `## Demo Or Walkthrough Notes`
- `## Examples`
- `## Frameworks, Models And Methodologies`
- `## Audience Questions`
- `## Takeaways`
- `## Applicable Actions`
- `## Risks Or Caveats`
- `## Source Limitations`

`detailed_notes.md` must include the executive overview inside the same document and must be rich enough to replace the old `summary.md` plus old `detailed_notes.md` pair. It must not copy or rewrite the transcript. Include tools, demos, examples, Q&A, caveats and source limitations when present.

If `selected_recipe = recipes/generic.md`, write `{{markdown_output_path}}` with these generic sections:

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

If `selected_recipe = recipes/meeting.md` or `recipes/technical_flow_meeting.md`, follow the selected meeting recipe and preserve its meeting-specific structure.

For webinar long-form outputs, do not write `{{markdown_output_path}}`. The Markdown output path is intentionally replaced by `{{detailed_notes_output_path}}`.

## Required JSON Outputs

Write `{{classification_output_path}}` following `schemas/classification.schema.json`.

Classification must include `selected_analysis_schema`. Use `schemas/webinar_analysis.schema.json` for webinar outputs and `schemas/generic_analysis.schema.json` for generic outputs.

If `selected_recipe = recipes/webinar.md` or `type = webinar`, write `{{analysis_output_path}}` following `schemas/webinar_analysis.schema.json`.

For webinar JSON, include:

- `schema_version`
- `content_type`
- `title`
- `executive_summary`
- `detailed_summary`
- `content_map`
- `key_concepts`
- `tools_mentioned`
- `demos_or_walkthroughs`
- `examples`
- `frameworks_or_models`
- `audience_questions`
- `takeaways`
- `applicable_actions`
- `risks_or_caveats`
- `source_limitations`

If `selected_recipe = recipes/generic.md`, write `{{analysis_output_path}}` following `schemas/generic_analysis.schema.json`.

If another specific recipe has a specific schema, use that schema. Otherwise follow the selected recipe structure without forcing webinar or generic fields.

## Content Contamination Check

Before saving the primary Markdown output and `analysis.json`, verify that no project instruction or operational metadata has leaked into meeting content.

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
- for webinar long-form outputs, only `detailed_notes.md` is written as the Markdown deliverable and `summary.md` is not updated;
- the generated prompt was saved;
- facts and interpretations are not mixed;
- decisions and action items are only present when supported by the transcript;
- confirmed decisions have explicit support in the transcript.
