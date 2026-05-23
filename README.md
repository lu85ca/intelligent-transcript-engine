# Intelligent Transcript Engine

`intelligent-transcript-engine` e' un progetto per analizzare file di trascrizione testuale.

L'obiettivo e' classificare automaticamente il tipo di contenuto e scegliere la strategia migliore per estrarre le informazioni piu' utili nel formato piu' adatto.

## Struttura

- `AGENTS.md`: regole operative per Codex e per gli agenti che lavorano sul progetto.
- `input/transcripts/`: trascrizioni sorgenti da analizzare.
- `output/markdown/`: risultati leggibili in Markdown.
- `output/json/`: risultati strutturati in JSON.
- `recipes/`: istruzioni di analisi per tipo di contenuto.
- `schemas/`: schemi JSON per classificazione e output.
- `scripts/`: script di supporto.
- `examples/`: esempi e materiale dimostrativo.
- `.agents/skills/transcript-intelligence/`: skill locale dedicata alla transcript intelligence.

## Flusso previsto

1. Inserire una trascrizione in `input/transcripts/`.
2. Eseguire la classificazione del contenuto.
3. Selezionare la recipe appropriata.
4. Estrarre fatti, interpretazioni, decisioni, azioni e domande aperte.
5. Generare output Markdown e JSON.

## Stato attuale

Scaffolding iniziale. La pipeline completa non e' ancora implementata.
