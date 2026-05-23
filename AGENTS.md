# Regole operative per Codex

Questo progetto analizza trascrizioni testuali con un workflow agent-driven. Codex legge trascrizione, regole, skill, recipe, template e schemi, poi genera direttamente prompt di debug, output Markdown e output JSON.

## Regole fondamentali

- Ogni transcript deve essere classificato prima di qualsiasi analisi.
- Non inventare informazioni, dettagli, intenzioni, nomi, date, decisioni o azioni non presenti nella trascrizione.
- Non fare assunzioni non supportate dal testo. Se una conclusione e' inferita, deve essere indicata come interpretazione.
- Se un dato manca, e' ambiguo o non e' deducibile con chiarezza, usare `non rilevato`.
- Non inserire minutaggi, timestamp o timecode nell'output finale.
- Separare sempre:
  - fatti
  - interpretazioni
  - decisioni
  - azioni
  - domande aperte
- L'output finale deve sempre essere prodotto in due formati:
  - Markdown leggibile in `output/markdown/`
  - JSON strutturato in `output/json/`
- Salvare sempre anche il prompt generato in `output/prompts/` con suffisso `_generated_prompt.md`.
- Il progetto deve restare incrementale, semplice e senza dipendenze non approvate.
- Non aggiungere script, dipendenze, API esterne o automazioni non richieste.
- Ogni nuova funzionalita' deve essere piccola, testabile e coerente con la struttura esistente.

## Workflow agent-driven

Per ogni trascrizione in `input/transcripts/`, Codex deve:

1. Leggere questo file `AGENTS.md`.
2. Usare la skill `.agents/skills/transcript-intelligence/SKILL.md`.
3. Leggere la trascrizione richiesta.
4. Classificare il tipo di contenuto con `type`, `confidence`, `secondary_type`, `signals`, `reason` e `recommended_recipe`.
5. Scegliere la recipe piu' adatta da `recipes/`.
6. Leggere `prompt_templates/meta_prompt.md` e `prompt_templates/final_analysis_prompt.md`.
7. Generare un prompt ottimizzato per la trascrizione specifica.
8. Salvare il prompt in `output/prompts/<nome>_generated_prompt.md`.
9. Applicare il prompt alla trascrizione.
10. Salvare la classificazione in `output/json/<nome>_classification.json`.
11. Salvare l'analisi strutturata in `output/json/<nome>_analysis.json`.
12. Salvare il riepilogo leggibile in `output/markdown/<nome>_summary.md`.
13. Fare un controllo qualita' finale su completezza, tracciabilita', assenza di invenzioni e rispetto degli schemi.

## Output atteso

Per `input/transcripts/example.md`, quando richiesto, Codex deve produrre:

- `output/prompts/example_generated_prompt.md`
- `output/markdown/example_summary.md`
- `output/json/example_analysis.json`
- `output/json/example_classification.json`
