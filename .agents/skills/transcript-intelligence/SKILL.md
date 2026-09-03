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
- For video/audio requests such as "riassumi questo video", "ho messo un video in input/videos" or "analizza l'ultimo video", run the deterministic Step 6A preprocessing runner first.
- For requests to process newly uploaded videos when raw transcripts are missing, this is mandatory: do not run `scripts/transcribe_audio_whisper.py` directly, do not use a foreground `scripts/process_videos.sh` run, do not poll the process, and do not stay in chat while local OpenAI Whisper runs. Start background transcription with `python3 scripts/start_transcription_batch.py`, report PID/log/check commands and stop immediately. Do not make further tool calls to monitor transcription unless the user explicitly asks. The user will send a new message when transcription is complete.
- If the Step 6A pipeline report has `ready_for_agent_analysis: false`, stop and ask for review instead of producing final summary, analysis or classification.
- If the Step 6A pipeline report is ready, use only `selected_transcript` as source content for the agent-driven workflow.
- If the user asks for a PDF, generate the Markdown/JSON outputs first, then run Step 7 with `scripts/export_summary_pdf.py` on the generated primary Markdown.
- Pipeline reports, review reports, normalization reports, candidate files, quality warnings, normalization candidates, technical logs and frontmatter are operational metadata. Do not turn them into narrative content.
- The PDF export script is deterministic: it converts an existing Markdown file to PDF with Pandoc, does not create new content, does not modify the source Markdown, and does not invoke Codex CLI.
- For long webinars, round tables, demos or sessions with many tools/Q&A, do not force the generic analysis structure. Use `recipes/webinar.md`, `schemas/webinar_analysis.schema.json`, and create `output/markdown/<name>_detailed_notes.md` as the only primary Markdown output.
- Do not create or update `summary.md` for long webinar or round table outputs. If `summary.md` already exists from a previous run, treat it as legacy/stale.
- Webinar outputs must separate tools mentioned, demos or walkthroughs, examples, frameworks or models, audience questions, takeaways, applicable actions and risks or caveats.
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
3. For video/audio or unprepared inputs, first check whether raw transcripts already exist.
4. If raw transcripts are missing for newly uploaded videos, run only `python3 scripts/start_transcription_batch.py`, provide the PID, log path, check commands and the exact follow-up message, then stop immediately. Do not monitor, poll or continue to Step 6A in the same turn.
5. After the user confirms transcription is complete in a later message, run Step 6A with `scripts/run_preprocessing_pipeline.py`.
6. For generic requests about the latest uploaded video, use `--latest-video` when the input is unambiguous enough; otherwise ask which file to use.
7. Read the Step 6A pipeline report.
8. If `ready_for_agent_analysis` is false, stop and ask for review/manual verification without producing final summary, analysis or classification.
9. Select the analysis transcript from `selected_transcript`, or with the project policy: normalized > reviewed > raw safe.
10. Read only the selected transcript from `input/transcripts/` as source content.
11. Lightly clean the transcript mentally: remove obvious noise, normalize spacing and preserve meaning.
12. Classify the content with `type` and, when useful, `subtype`.
13. Select the most suitable recipe from `recipes/`.
14. If the transcript clearly matches a domain profile, read the relevant file from `domain_profiles/`.
15. Read `prompt_templates/meta_prompt.md`.
16. Read `prompt_templates/final_analysis_prompt.md`.
17. Generate the optimized final prompt for the selected transcript.
18. Save it as `output/prompts/<name>_generated_prompt.md`.
19. Apply the generated prompt to the selected transcript.
20. Save the primary Markdown output. For generic/meeting/youtube flows this is usually `output/markdown/<name>_summary.md`; for long webinars or round tables this is only `output/markdown/<name>_detailed_notes.md`.
21. Save JSON analysis to `output/json/<name>_analysis.json`.
22. Save JSON classification to `output/json/<name>_classification.json`.
23. For long webinars or round tables, do not create or update `output/markdown/<name>_summary.md`.
24. If the user requested PDF export, run `python3 scripts/export_summary_pdf.py "<primary markdown path>" --output-dir "output/pdf"` unless the user requested a different output directory. For long webinars, the primary markdown path is `output/markdown/<name>_detailed_notes.md`.
25. If `candidate_count > 0`, mention candidates only in a separate operational note after the final outputs and suggest `python3 scripts/manage_candidates.py list --context <context>`.
26. Run a final quality check.

## Classification

Classification must include:

- `type`: primary content type.
- `subtype`: specialized subtype, or `non rilevato`.
- `confidence`: score from 0 to 1.
- `secondary_type`: alternate plausible type, or `non rilevato`.
- `selected_recipe`: recipe file to use.
- `selected_analysis_schema`: analysis schema file to use.
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

## Webinar Outputs

For webinars, use `schemas/webinar_analysis.schema.json` instead of the generic schema. The webinar analysis must include executive summary, detailed summary, content map, key concepts, tools mentioned, demos or walkthroughs, examples, frameworks or models, audience questions, takeaways, applicable actions, risks or caveats and source limitations when supported by the transcript.

For long webinars or round tables, generate `output/markdown/<name>_detailed_notes.md` as the only Markdown deliverable. This file must include the executive overview and detailed thematic coverage in one document, but it must not copy the transcript or include technical pipeline metadata. Do not create or update `summary.md` for this flow.

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
- For webinar outputs, confirm that the webinar schema and webinar-specific Markdown sections were used.
- For long webinars, confirm that `detailed_notes.md` exists as the only Markdown deliverable and `summary.md` was not updated.
- If requested, confirm that PDF export was performed from the generated primary Markdown, not by generating new content.
- Confirm that the generated prompt is saved.
- Confirm that facts, interpretations, decisions, actions and open questions are separate.
- Confirm that only `selected_transcript` was used as source content for video/audio requests.
- Confirm that technical pipeline metadata and candidate suggestions did not enter final content.
