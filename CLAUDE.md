# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`intelligent-transcript-engine` turns video, audio, or transcripts into structured Markdown/JSON/PDF summaries. It is split into two strictly separated halves:

- **Deterministic preprocessing** (`scripts/*.py`, all Python, no LLM calls): audio extraction, MLX Whisper transcription, review, normalization, candidate-glossary collection, transcript selection, PDF export.
- **Agent-driven workflow** (governed by [AGENTS.md](AGENTS.md) and `.agents/skills/transcript-intelligence/SKILL.md`, executed by Codex/Claude reading transcript + recipes + schemas): classification, recipe selection, prompt generation, and the final Markdown/JSON outputs.

**`AGENTS.md` is the actual source of truth for how to operate in this repo** — it is long and detailed (rules on classification, knowledge/candidate promotion, webinar vs. non-webinar output, when to background the transcription batch job, anti-hallucination rules, separation of "source content" vs. "operational metadata"). Read it before doing any transcript-analysis work; do not duplicate its rules from memory, re-read it, since it is the canonical spec and may be updated independently of this file.

## Commands

There is no build step; this is a pure-Python (stdlib-only, no `requirements.txt`/`pyproject.toml`) scripts project plus a set of Markdown/YAML/JSON "knowledge" and prompt assets.

Run a specific test module (tests use `unittest`, not pytest — pytest is not installed):

```bash
python3 -m unittest tests.test_run_preprocessing_pipeline -v
```

Run a single test case/method:

```bash
python3 -m unittest tests.test_normalize_transcript.TestClassName.test_method_name -v
```

Run the whole suite:

```bash
python3 -m unittest discover -s tests -v
```

Each test file loads the target script directly via `importlib.util.spec_from_file_location` (scripts are not an installed package), so tests must be run from the repo root.

Core pipeline entry points (see AGENTS.md for full usage and constraints):

```bash
python3 scripts/run_preprocessing_pipeline.py --latest-video --context work_meetings --json
python3 scripts/run_preprocessing_pipeline.py "NOME_BASE" --context work_meetings --dry-run --json
python3 scripts/select_analysis_transcript.py "NOME_BASE" --json
python3 scripts/normalize_transcript.py "NOME_BASE" --context work_meetings --force
python3 scripts/manage_candidates.py collect|list|promote|reject --context work_meetings --json
python3 scripts/export_summary_pdf.py "<path/to/markdown.md>" --output-dir "output/pdf"
python3 scripts/start_transcription_batch.py   # background MLX Whisper batch — never run transcribe_audio_mlx.py or process_videos.sh directly/foreground
```

`export_summary_pdf.py` requires Pandoc (`pandoc` on PATH); transcription requires `mlx_whisper` — neither is installed in every environment, so tests mock/stub around them rather than requiring them.

## Architecture

### Directory roles

- `input/videos/`, `input/audio/` — source media (gitignored, along with all of `input/` and `output/`).
- `input/transcripts/{raw,reviewed,normalized}/` — successive preprocessing stages of a transcript.
- `output/{preprocessing,transcription,review,normalization,pipeline}/` — technical/debug reports from each deterministic step. These are **operational metadata**: never treated as meeting/video content.
- `output/prompts/<name>_generated_prompt.md` — the agent-generated prompt (debug artifact, not a final output).
- `output/markdown/<name>_summary.md` — primary Markdown output for non-webinar content.
- `output/markdown/<name>_detailed_notes.md` — primary Markdown output for long webinars/round tables (mutually exclusive with `_summary.md` — never both for the same content type).
- `output/json/<name>_classification.json`, `output/json/<name>_analysis.json` — structured outputs, validated against `schemas/*.schema.json`.
- `output/pdf/` — Pandoc-exported PDF of the primary Markdown, generated only on request.
- `recipes/*.md` — per-content-type analysis instructions (`meeting.md`, `technical_flow_meeting.md`, `webinar.md`, `youtube_video.md`, `generic.md`).
- `domain_profiles/*.md` — optional domain-specific term normalization (e.g. `sige_imu_document_flow.md`); only used when the transcript clearly matches, never a source of new facts.
- `prompt_templates/{meta_prompt.md,final_analysis_prompt.md}` — templates the agent reads to build the generated prompt.
- `knowledge/global/`, `knowledge/work_meetings/`, `knowledge/macro_categories/{finance,travel,social_media_management,generic}/` — incremental, versioned domain knowledge (`approved_terms.yml`, `normalization_rules.yml`, `context.md`, `candidates/`, `examples/`); selection logic is in `knowledge/registry.yml`.
- `.agents/skills/transcript-intelligence/SKILL.md` — the Codex/Claude skill definition mirroring AGENTS.md's rules for the agent-driven step.

### The preprocessing → agent-driven pipeline

```
video/audio -> raw transcript -> quality report -> reviewed transcript
  -> normalized transcript -> candidate glossary -> selected transcript
  -> [agent-driven] classification -> recipe + knowledge selection -> generated_prompt.md
  -> primary Markdown (summary.md OR detailed_notes.md) -> classification.json -> analysis.json
  -> (optional) PDF export
```

`run_preprocessing_pipeline.py` orchestrates Steps 1–6A (deterministic) and reports `pipeline_status` / `ready_for_agent_analysis` / `selected_transcript`. **No script in this repo invokes Codex/Claude CLI or writes summary/classification/analysis output** — that only happens in the agent-driven step (Step 6B onward), reading `selected_transcript` as the sole source of content.

Transcript selection policy: `normalized > reviewed > raw` (raw only if its technical JSON marks `safe_for_analysis: true`); otherwise stop and require manual review rather than producing final output.

### Candidate/knowledge promotion model

Three tiers, never auto-promoted: `candidate` (suggestion in `knowledge/<context>/candidates/`) → `approved_terms.yml` (canonical glossary) → `normalization_rules.yml` (actually applied automatically during normalization). Promotion is always a manual `manage_candidates.py promote` call; Step 3 normalization never reads `candidates/`.

### Content vs. operational-metadata separation

This is the central invariant enforced throughout AGENTS.md, the skill file, and prompt templates: everything under `recipes/`, `domain_profiles/`, `knowledge/`, `schemas/`, `prompt_templates/`, technical reports in `output/{preprocessing,transcription,review,normalization,pipeline}/`, and `generated_prompt.md` is *operational metadata* that guides analysis but must never appear as meeting/video content, source, or justification in final `analysis.json`/Markdown fields (no "according to the recipe/domain profile/knowledge context" language). Only the selected transcript itself is a valid source for facts, decisions, hypotheses, actions, risks, and open questions. When in doubt about a decision's confirmation strength, prefer weaker categories (orientation/hypothesis/open point) over "confirmed decision."

### Webinar vs. non-webinar output shape

If classification resolves to `type: webinar` (`recipes/webinar.md`, `schemas/webinar_analysis.schema.json`), the primary output is *only* `detailed_notes.md` — never generate or update `summary.md` for these, and treat any stale `summary.md` from a prior run as legacy. All other types produce `summary.md` via `schemas/generic_analysis.schema.json`.
