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
2. Pulire leggermente il testo senza modificare il significato.
3. Classificare il contenuto con `type`, `confidence`, `secondary_type`, `signals` e `reason`.
4. Selezionare la recipe appropriata.
5. Estrarre informazioni strutturate in base alla recipe.
6. Separare fatti, interpretazioni, decisioni, action item, rischi, follow-up e domande aperte.
7. Generare output Markdown e JSON.
8. Eseguire un controllo qualita' finale per evitare informazioni inventate.

## Metodo

La classificazione guida la strategia di analisi. Quando il tipo di contenuto e' ambiguo, il sistema deve indicare un `secondary_type`, abbassare la `confidence` e usare la recipe `generic` se non ci sono segnali sufficienti.

Le informazioni assenti devono essere marcate come `non rilevato`. Le interpretazioni devono restare separate dai fatti espliciti.

## Utilizzo

Esegui la pipeline locale su una trascrizione Markdown:

```bash
python3 scripts/run_pipeline.py input/transcripts/example.md
```

La pipeline genera:

- `output/json/example_classification.json`
- `output/json/example_analysis.json`
- `output/markdown/example_summary.md`

## Stato attuale

Prima versione locale rule-based. La logica AI e le chiamate API non sono ancora implementate.
