# Regole operative per Codex

Questo progetto analizza trascrizioni testuali, classifica il tipo di contenuto e sceglie la strategia di analisi piu' utile. Mantieni il lavoro semplice, verificabile e incrementale.

## Regole fondamentali

- Ogni transcript deve essere classificato prima di qualsiasi analisi.
- Non inventare informazioni, dettagli, intenzioni, nomi, date, decisioni o azioni non presenti nella trascrizione.
- Non fare assunzioni non supportate dal testo. Se una conclusione e' inferita, deve essere indicata come interpretazione.
- Se un dato manca, e' ambiguo o non e' deducibile con chiarezza, usare `non rilevato`.
- Separare sempre:
  - fatti
  - interpretazioni
  - decisioni
  - azioni
  - domande aperte
- L'output finale deve sempre essere prodotto in due formati:
  - Markdown leggibile in `output/markdown/`
  - JSON strutturato in `output/json/`
- Il progetto deve restare incrementale, semplice e senza dipendenze non approvate.
- Ogni nuova funzionalita' deve essere piccola, testabile e coerente con la struttura esistente.

## Flusso previsto

1. Ricevere un file di trascrizione.
2. Pulire leggermente il testo senza alterarne il significato.
3. Classificare il tipo di contenuto.
4. Registrare confidence, segnali e motivazione della classificazione.
5. Selezionare la recipe piu' adatta.
6. Estrarre le informazioni richieste senza aggiungere contenuto non presente.
7. Salvare il risultato in Markdown e JSON.
8. Fare un controllo qualita' finale su completezza, tracciabilita' e assenza di invenzioni.
