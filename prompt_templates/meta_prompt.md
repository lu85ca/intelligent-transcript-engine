# Meta Prompt Template

Use this template to generate the best final analysis prompt for a specific transcript.

## Inputs

- Transcript path: `{{transcript_path}}`
- Transcript content: `{{transcript}}`
- Global rules from `AGENTS.md`: `{{global_rules}}`
- Transcript intelligence skill: `{{skill_instructions}}`
- Classification result: `{{classification}}`
- Selected recipe: `{{selected_recipe}}`
- Output schemas: `{{schemas}}`

## Goal

Generate a focused final prompt that will analyze the transcript according to:

- the classified transcript type;
- the selected recipe;
- the global project rules;
- the required Markdown and JSON output contracts;
- the specific content and limitations of the transcript.

## Required Behavior

The generated prompt must instruct the agent to:

- classify before analysis;
- avoid timestamps or timecodes in the final output;
- avoid invented information;
- use `non rilevato` when data is missing or unclear;
- separate facts, interpretations, decisions, actions and open questions;
- produce Markdown and JSON outputs;
- save classification JSON, analysis JSON and summary Markdown;
- preserve source limitations;
- keep the workflow simple and incremental.

## Generated Prompt Requirements

The generated prompt must include:

- transcript type and confidence;
- selected recipe path;
- relevant signals from classification;
- exact output file paths;
- required Markdown sections;
- required JSON fields;
- final quality checklist.

The generated prompt may be saved as `output/prompts/<name>_generated_prompt.md` for debugging. The user should not need to manually rerun it.
