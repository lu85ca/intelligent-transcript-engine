# Meta Prompt Template

Use this template to generate the best final analysis prompt for a specific transcript.

## Inputs

- Transcript path: `{{transcript_path}}`
- Transcript content: `{{transcript}}`
- Global rules from `AGENTS.md`: `{{global_rules}}`
- Transcript intelligence skill: `{{skill_instructions}}`
- Classification result: `{{classification}}`
- Selected recipe: `{{selected_recipe}}`
- Selected domain profile: `{{selected_domain_profile}}`
- Output schemas: `{{schemas}}`

## Source Separation

- Primary source: transcript.
- Operational context: AGENTS.md, skill, recipe, domain profile, schemas, templates and generated prompt.
- Rule: only the transcript can generate meeting facts, confirmed decisions, actions, hypotheses, technical orientations, risks, follow-ups and open questions.
- Operational context guides classification, normalization, structure and quality checks, but it is not meeting content and must not be cited as support inside final interpretations or normalization explanations.

## Goal

Generate a focused final prompt that will analyze the transcript according to:

- the classified transcript type;
- the classified transcript subtype;
- the selected recipe;
- the selected domain profile, if present;
- the global project rules;
- the required Markdown and JSON output contracts;
- the specific content and limitations of the transcript.

The generated prompt is an internal/debug artifact for Codex. It documents the operational prompt used by the agent and does not need to be a standalone copy-paste prompt for use outside this project.

It may reference workspace files, including the transcript path, AGENTS.md, skill file, recipe, domain profile and schemas. It is not required to embed the full transcript when Codex can read it from the workspace. It is not final reader-facing output.

## Required Behavior

The generated prompt must instruct the agent to:

- classify before analysis;
- include `type`, `subtype`, `selected_recipe` and `selected_domain_profile` in the classification;
- avoid timestamps or timecodes in the final output;
- avoid invented information;
- use `non rilevato` when data is missing or unclear;
- for technical or functional flows, use `non specificato nella trascrizione`, `da confermare` or `punto aperto` where more precise;
- avoid turning proposals, hypotheses or orientations into confirmed decisions;
- avoid including workflow/project instructions in the meeting analysis as if they were meeting content;
- use processing rules such as no timestamps, anti-hallucination rules, output format rules and missing-data conventions only as analysis constraints, not as meeting decisions, meeting facts, hypotheses, orientations or action items;
- never use AGENTS.md, skill instructions, recipe rules, templates, schemas, domain profiles or generated prompt text as source material for meeting content fields;
- never cite operational metadata as support in `interpretations` or normalization explanations;
- avoid forbidden formulas in final content, including "supportato dal domain profile", "secondo la recipe", "in base allo schema", "come indicato nel generated prompt" and "seguendo le istruzioni del workflow";
- explain domain normalizations only with transcript evidence, for example: "La normalizzazione di Stardus/Stardust come STARDAS è supportata dai riferimenti ripetuti al sistema documentale nella trascrizione.";
- if an application domain such as SIGE IMU is not explicitly stated in the transcript, keep it out of `analysis.json` content interpretations; it may appear only as `selected_domain_profile` in `classification.json`;
- separate facts, interpretations, decisions, actions and open questions;
- produce Markdown and JSON outputs;
- save classification JSON, analysis JSON and summary Markdown;
- preserve source limitations;
- keep the workflow simple and incremental.

## Generated Prompt Requirements

The generated prompt must include:

- transcript type and confidence;
- transcript subtype;
- selected recipe path;
- selected domain profile path, or `non rilevato`;
- global rules from `AGENTS.md`;
- rules from the selected recipe;
- rules from the selected domain profile, if present;
- explicit anti-hallucination constraints;
- relevant signals from classification;
- exact output file paths;
- required Markdown sections;
- required JSON fields;
- final quality checklist.

The generated prompt must be saved as `output/prompts/<name>_generated_prompt.md` for debugging. The user should not need to manually rerun it.

The generated prompt should document:

- classification chosen;
- selected recipe;
- selected domain profile, if any;
- rules applied;
- output structure;
- quality checklist.

The quality checklist must include a content contamination check before saving final outputs.
