# Transcript Intelligence Skill

Use this skill when Codex is asked to analyze a transcript in `input/transcripts/` with the agent-driven workflow. The skill covers classification, recipe selection, prompt generation, structured extraction, output writing and final quality control.

## Rules

- Always classify the transcript before analysis.
- Classification must include `type` and `subtype` when a subtype is useful.
- Do not invent facts that are not present in the transcript.
- Do not rely on unsupported assumptions. Mark inferred content as interpretation.
- Use `non rilevato` when information is absent or unclear.
- For technical or functional flows, use `non specificato nella trascrizione`, `da confermare` or `punto aperto` when appropriate.
- Do not turn proposals, hypotheses or orientations into confirmed decisions.
- Do not include workflow/project instructions in the meeting analysis as if they were meeting content.
- Processing rules such as no timestamps, anti-hallucination rules, output format rules and missing-data conventions must guide the analysis but must not appear as meeting decisions, meeting facts, hypotheses, orientations or action items.
- Treat AGENTS.md, this skill, recipes, templates, schemas, domain profiles, generated prompts, technical reports, candidate files, promotion logs and transcript-selection decisions as operational metadata, not as transcript content.
- The transcript is the only primary source for meeting facts, confirmed decisions, hypotheses, orientations, action items, risks, follow-ups and open questions.
- Operational metadata must not appear as a source or justification in final content, including `interpretations` and domain normalization explanations.
- Candidate suggestions are not approved terms or active normalization rules. Do not apply candidates unless they have been manually promoted into approved knowledge files.
- For video/audio requests, run the deterministic Step 6A preprocessing runner first. If the pipeline report is not ready for agent analysis, stop and ask for review instead of producing final outputs.
- Do not write phrases such as "supportato dal domain profile", "secondo la recipe", "in base allo schema", "come indicato nel generated prompt" or "seguendo le istruzioni del workflow" in final meeting-content fields.
- Domain normalizations may be explained only through textual evidence from the transcript. Correct: "La normalizzazione di Stardus/Stardust come STARDAS è supportata dai riferimenti ripetuti al sistema documentale nella trascrizione." Incorrect: "La normalizzazione è supportata dal domain profile."
- If an application domain such as SIGE IMU is not explicitly stated in the transcript, do not add it to `analysis.json` as a content interpretation. It may appear only as `selected_domain_profile` in `classification.json`.
- Do not include timestamps, timecodes or minute markers in final outputs.
- Always produce Markdown and JSON outputs.
- Always save the generated prompt in `output/prompts/`.
- Keep facts, interpretations, decisions, actions and open questions separate.
- Prefer small, incremental changes without unapproved external dependencies.
- Do not create scripts, external API calls or new automation unless explicitly requested.

## Agent-Driven Workflow

1. Read `AGENTS.md`.
2. Read this skill file.
3. For video/audio or unprepared inputs, run Step 6A with `scripts/run_preprocessing_pipeline.py`.
4. Select the analysis transcript with the project policy: normalized > reviewed > raw safe.
5. If the pipeline or selector decision is `requires_review`, stop and ask for review/manual verification without producing final summary, analysis or classification.
6. Read the selected transcript from `input/transcripts/`.
7. Lightly clean the transcript mentally: remove obvious noise, normalize spacing and preserve meaning.
8. Classify the content with `type` and, when useful, `subtype`.
9. Select the most suitable recipe from `recipes/`.
10. If the transcript clearly matches a domain profile, read the relevant file from `domain_profiles/`.
11. Read `prompt_templates/meta_prompt.md`.
12. Read `prompt_templates/final_analysis_prompt.md`.
13. Generate the optimized final prompt for the selected transcript.
14. Save it as `output/prompts/<name>_generated_prompt.md`.
15. Apply the generated prompt to the selected transcript.
16. Save Markdown output to `output/markdown/<name>_summary.md`.
17. Save JSON analysis to `output/json/<name>_analysis.json`.
18. Save JSON classification to `output/json/<name>_classification.json`.
19. Run a final quality check.

## Classification

Classification must include:

- `type`: primary content type.
- `subtype`: specialized subtype, or `non rilevato`.
- `confidence`: score from 0 to 1.
- `secondary_type`: alternate plausible type, or `non rilevato`.
- `selected_recipe`: recipe file to use.
- `selected_domain_profile`: domain profile file to use, or `non rilevato`.
- `signals`: textual clues that support the classification.
- `reason`: concise explanation.

For ambiguous transcripts, lower the confidence score and fill `secondary_type`. If the transcript does not clearly match a known type, use `generic` and `recipes/generic.md`.

For meetings, distinguish:

- `subtype: generic_meeting`: ordinary coordination, review, planning or decision meeting.
- `subtype: technical_flow_meeting`: meeting focused on reconstructing an end-to-end technical, functional or application flow.

When `subtype` is `technical_flow_meeting`, prefer `recipes/technical_flow_meeting.md`.

## Domain Profiles

Use files in `domain_profiles/` only when the transcript clearly matches that domain or the user explicitly asks for that profile.

Domain profiles help normalize domain terminology and preserve domain-specific constraints. They must not make Codex invent missing systems, integrations, decisions, states, owners or dates.

If a domain profile is used, set `selected_domain_profile` in the classification. If none is used, set it to `non rilevato`.

Domain profiles can guide normalization and interpretation of terms already present in the transcript. They are not a primary source for meeting content and must not add facts, interpretations, decisions, actions, risks or open questions that are absent from the transcript. When documenting a normalization in final content, cite only transcript evidence, never the domain profile itself.

## Prompt Debugging

Generated prompts must be saved for debugging and reproducibility. The generated prompt is an internal/debug artifact for Codex: it documents the operational prompt used by the agent, the classification, selected recipe, selected domain profile, applied rules, output structure and quality checklist.

It does not need to be a standalone copy-paste prompt for use outside the project. It may reference workspace files instead of embedding the full transcript when Codex can read those files directly.

The generated prompt is not a primary information source and must not be analyzed as if it were part of the transcript. It is useful for traceability and reproducibility of the workflow, not as final reader-facing output.

For `input/transcripts/example.md`, expected debug prompt path:

- `output/prompts/example_generated_prompt.md`

## Final Quality Check

- Confirm that classification happened before analysis.
- Before writing final outputs, verify that no project/workflow instruction has leaked into meeting content fields.
- Confirm that no timestamps or timecodes are included.
- Confirm that unsupported claims are absent.
- Confirm that missing fields use `non rilevato`.
- Confirm that technical flow gaps use `non specificato nella trascrizione`, `da confermare` or `punto aperto` where more precise than `non rilevato`.
- Confirm that project/workflow instructions are not reported as meeting content.
- Confirm that AGENTS.md, skill instructions, recipes, templates, schemas, domain profiles and generated prompt content did not become meeting facts, interpretations, decisions, hypotheses, orientations, action items, risks, follow-ups or open questions.
- Confirm that domain normalization explanations are based only on transcript evidence and do not cite operational metadata.
- Confirm that proposals and hypotheses are not reported as confirmed decisions.
- Confirm that confirmed decisions have explicit support in the transcript.
- Confirm that Markdown and JSON are both produced.
- Confirm that the generated prompt is saved.
- Confirm that facts, interpretations, decisions, actions and open questions are separate.
