# Technical Flow Meeting Recipe

Usa questa recipe quando una riunione descrive un flusso tecnico, funzionale o applicativo end-to-end. L’obiettivo è ricostruire sistemi coinvolti, stati, componenti, integrazioni, decisioni, punti aperti e attività operative.

## Quando usarla

- La riunione è focalizzata sulla ricostruzione di un flusso applicativo o documentale.
- I partecipanti discutono sistemi, componenti, integrazioni, stati, servizi, dati o documenti.
- Emergono passaggi sequenziali del tipo: input, elaborazione, invio, ricezione, protocollazione, archiviazione, stato finale.
- Ci sono domande tecniche o funzionali da chiarire.
- La trascrizione contiene decisioni, ipotesi, proposte e attività operative legate al flusso.

## Segnali da riconoscere

- Riferimenti a sistemi o componenti applicativi.
- Descrizione di stati, cambi stato, esiti, eventi o code.
- Discussione di integrazioni, API, servizi, batch, chiamate o scambi dati.
- Ricostruzione di sequenze operative o end-to-end.
- Confronto tra ciò che è già implementato, da implementare o da verificare.
- Presenza di punti tecnici aperti.

## Output Markdown

Il documento finale deve usare questa struttura:

# 1. Executive summary

Sintesi breve del flusso discusso, delle decisioni principali e dei punti ancora aperti.

# 2. Contesto generale

Descrivere il contesto della riunione, l’obiettivo del confronto e il perimetro del flusso. Se non è chiaro, usare `non specificato nella trascrizione`.

# 3. Sistemi e componenti coinvolti

Usare questa tabella:

| Sistema / componente | Ruolo nel flusso | Informazioni emerse | Punti da chiarire |
| --- | --- | --- | --- |

# 4. Flusso end-to-end ricostruito

Questa è la sezione più importante.

Il flusso deve essere sequenziale e numerato. Per ogni step indicare:

- cosa succede;
- componente coinvolto;
- documento/dato prodotto o modificato;
- stato modificato, se citato;
- cosa è già implementato;
- cosa è da implementare;
- cosa è da verificare.

Se un elemento non è specificato, usare `non specificato nella trascrizione`, `da confermare` o `punto aperto`.

# 5. Diagramma testuale del flusso

Usare un diagramma testuale semplice con frecce, senza inventare step non supportati.

Esempio di formato:

```text
Sistema A -> Sistema B -> Sistema C
```

# 6. Decisioni, ipotesi e orientamenti

Separare chiaramente:

- decisioni confermate;
- orientamenti tecnici;
- ipotesi emerse;
- proposte non confermate.

Decisioni confermate è una categoria restrittiva. Deve contenere solo decisioni supportate esplicitamente dalla trascrizione, con evidenza di accordo, deliberazione o scelta già assunta.

Non trasformare proposte, preferenze tecniche, opzioni, ipotesi, ricostruzioni del flusso, interpretazioni o orientamenti operativi in decisioni definitive.

Una ricostruzione del flusso non è automaticamente una decisione. Una preferenza tecnica non è automaticamente una decisione. Una proposta operativa non è automaticamente una decisione.

Le regole di processamento del progetto non sono contenuto della riunione. Regole come non inserire minutaggi, non inventare informazioni, produrre Markdown/JSON o usare convenzioni per dati mancanti devono guidare l’analisi, ma non devono comparire tra decisioni, fatti, ipotesi, orientamenti o attività della riunione.

Regola pratica: se una voce potrebbe iniziare con “il report deve...” oppure “l’agente deve...” ed è collegata al workflow di analisi, allora è quasi certamente una regola del progetto e non contenuto della riunione.

Se il supporto testuale è debole, classificare la voce come orientamento tecnico, ipotesi emersa, proposta non confermata o punto aperto.

# 7. Punti tecnici aperti

Elencare dubbi tecnici, verifiche richieste, ambiguità e informazioni mancanti.

# 8. Attività operative

Usare questa tabella:

| Attività | Owner | Scadenza | Evidenza | Note |
| --- | --- | --- | --- | --- |

# 9. Source limitations

Indicare limiti della trascrizione, informazioni mancanti, ambiguità terminologiche e passaggi non confermati.

## Campi JSON consigliati

Quando lo schema specifico non esiste ancora, usare `schemas/generic_analysis.schema.json` come contratto minimo e mappare:

- `title`
- `content_type`
- `summary`
- `key_points`
- `facts`
- `interpretations`
- `decisions`
- `action_items`
- `open_questions`
- `risks`
- `followups`
- `source_limitations`

Se serve preservare dettagli tecnici non coperti dallo schema generico, inserirli in modo testuale dentro `key_points`, `facts`, `open_questions`, `followups` e `source_limitations`, senza aggiungere campi fuori schema.

## Cosa non inventare

- Non inventare sistemi, componenti, integrazioni, API, stati o documenti.
- Non inventare owner, scadenze o responsabilità.
- Non dedurre implementazioni già presenti se non sono citate.
- Non trasformare proposte o ipotesi in decisioni confermate.
- Non trattare regole del workflow transcript-intelligence come contenuto della riunione.
- Non inserire regole di processamento tra decisioni, fatti, ipotesi, orientamenti o attività operative.
- Non inserire minutaggi.
- Se qualcosa non è specificato, usare `non specificato nella trascrizione`, `da confermare` o `punto aperto`.
