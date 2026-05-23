# Transcript Intelligence Skill

Use this skill when working on transcript classification and analysis for this project.

## Rules

- Always classify the transcript before analysis.
- Do not invent facts that are not present in the transcript.
- Use `non rilevato` when information is absent or unclear.
- Always produce Markdown and JSON outputs.
- Keep facts, interpretations, decisions, actions and open questions separate.
- Prefer small, incremental changes.

## Expected Workflow

1. Read the transcript.
2. Classify the content type.
3. Select the matching recipe from `recipes/`.
4. Extract useful information according to the recipe.
5. Write Markdown output to `output/markdown/`.
6. Write JSON output to `output/json/`.
