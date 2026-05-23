# Intelligent Transcript Engine

`intelligent-transcript-engine` e' un progetto agent-driven per analizzare file di trascrizione testuale.

L'obiettivo e' far lavorare Codex come agente: leggere regole, skill, recipe, template e trascrizione, classificare il contenuto, generare un prompt ottimizzato e produrre output Markdown e JSON.

Il progetto non usa piu' uno script Python come pipeline principale. Codex/AI e' responsabile di classificare, scegliere la recipe, generare il prompt, applicarlo e salvare gli output.

## Struttura

- `AGENTS.md`: regole operative per Codex e per gli agenti che lavorano sul progetto.
- `input/transcripts/`: trascrizioni sorgenti da analizzare.
- `output/markdown/`: risultati leggibili in Markdown.
- `output/json/`: risultati strutturati in JSON.
- `output/prompts/`: prompt generati per debug e riproducibilita'.
- `prompt_templates/`: template per generare e applicare prompt di analisi.
- `recipes/`: istruzioni di analisi per tipo di contenuto.
- `schemas/`: schemi JSON per classificazione e output.
- `examples/`: esempi e materiale dimostrativo.
- `.agents/skills/transcript-intelligence/`: skill locale dedicata alla transcript intelligence.

## Flusso agent-driven

1. Inserire una trascrizione in `input/transcripts/`.
2. Codex legge `AGENTS.md`.
3. Codex usa `.agents/skills/transcript-intelligence/SKILL.md`.
4. Codex classifica la trascrizione.
5. Codex sceglie la recipe piu' adatta da `recipes/`.
6. Codex usa i template in `prompt_templates/` per generare un prompt ottimizzato.
7. Codex salva il prompt in `output/prompts/<nome>_generated_prompt.md`.
8. Codex applica il prompt alla trascrizione.
9. Codex salva:
   - `output/json/<nome>_classification.json`
   - `output/json/<nome>_analysis.json`
   - `output/markdown/<nome>_summary.md`

## Metodo

La classificazione guida la strategia di analisi. Quando il tipo di contenuto e' ambiguo, il sistema deve indicare un `secondary_type`, abbassare la `confidence` e usare la recipe `generic` se non ci sono segnali sufficienti.

Le informazioni assenti devono essere marcate come `non rilevato`. Le interpretazioni devono restare separate dai fatti espliciti.

Regole obbligatorie:

- non inserire minutaggi nell'output;
- non inventare informazioni;
- classificare sempre prima di analizzare;
- salvare sempre il prompt generato;
- produrre sempre Markdown e JSON;
- non aggiungere dipendenze, API esterne o nuovi script.

## How to use with Codex CLI

Esempio pratico:

```bash
codex "Analizza input/transcripts/example.md seguendo AGENTS.md, la skill transcript-intelligence, le recipe, gli schema e i prompt template. Genera output/prompts/example_generated_prompt.md, output/json/example_classification.json, output/json/example_analysis.json e output/markdown/example_summary.md."
```

Output atteso:

- `output/prompts/example_generated_prompt.md`
- `output/json/example_classification.json`
- `output/json/example_analysis.json`
- `output/markdown/example_summary.md`

## Stato attuale

Workflow agent-driven documentato. Non ci sono script di pipeline, dipendenze esterne o chiamate API implementate.
