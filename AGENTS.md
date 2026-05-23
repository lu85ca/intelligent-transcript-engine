# Regole operative per Codex

Questo progetto analizza trascrizioni testuali e produce output strutturati. Mantieni il lavoro semplice, verificabile e incrementale.

## Regole fondamentali

- Non inventare informazioni non presenti nella trascrizione.
- Classificare sempre la trascrizione prima di analizzarla.
- Se un'informazione non e' presente o non e' deducibile con chiarezza, usare `non rilevato`.
- Produrre sempre due output per ogni analisi:
  - Markdown leggibile in `output/markdown/`
  - JSON strutturato in `output/json/`
- Separare sempre:
  - fatti
  - interpretazioni
  - decisioni
  - azioni
  - domande aperte
- Preferire soluzioni semplici e incrementali.
- Non aggiungere dipendenze esterne senza una ragione chiara.
- Ogni nuova funzionalita' deve essere piccola, testabile e coerente con la struttura esistente.

## Flusso previsto

1. Ricevere un file di trascrizione.
2. Classificare il tipo di contenuto.
3. Selezionare la recipe piu' adatta.
4. Estrarre le informazioni richieste senza aggiungere contenuto non presente.
5. Salvare il risultato in Markdown e JSON.
