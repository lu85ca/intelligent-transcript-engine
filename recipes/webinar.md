# Webinar Recipe

Usa questa recipe quando la trascrizione rappresenta un webinar, una presentazione educativa, una round table, una demo guidata, un workshop o una sessione formativa.

## Quando Usarla

- Webinar live o registrati.
- Presentazioni didattiche, workshop, masterclass o sessioni formative.
- Round table con spiegazioni, demo, esempi e domande del pubblico.
- Contenuti con strumenti, workflow operativi, framework, modelli, Q&A o walkthrough.

## Segnali Da Riconoscere

- Introduzione di relatore, tema, pubblico o obiettivo della sessione.
- Struttura didattica con sezioni, framework, step o progressione dimostrativa.
- Domande del pubblico e risposte del relatore.
- Citazioni di strumenti, modelli, esempi, asset, risorse o demo.
- Discussione di limiti, vincoli, contesti d'uso o prossimi approfondimenti.

## Obiettivo Dell'Output

Per webinar lunghi e round table, il documento Markdown finale primario deve essere uno solo:

```text
output/markdown/<nome>_detailed_notes.md
```

Non generare `summary.md` per webinar lunghi o round table. Se `summary.md` esiste da una run precedente, considerarlo legacy/stale e non aggiornarlo.

`detailed_notes.md` deve essere abbastanza ricco da sostituire sia il vecchio summary sia le vecchie note dettagliate: deve contenere una panoramica esecutiva breve ma utile e poi copertura estesa dei temi.

`generated_prompt.md` resta un artefatto interno/debug. `classification.json` e `analysis.json` restano output strutturati obbligatori.

## Output Markdown: detailed_notes.md

Per webinar lunghi o round table, usare `output/markdown/<nome>_detailed_notes.md` come unico deliverable Markdown:

- `# Webinar Detailed Notes`
- `## Classification`
- `## Executive Overview`
- `## Content Map`
- `## Detailed Thematic Sections`
- `## Key Concepts`
- `## Tools, Platforms And Assets Mentioned`
- `## Demo Or Walkthrough Notes`
- `## Examples`
- `## Frameworks, Models And Methodologies`
- `## Audience Questions`
- `## Takeaways`
- `## Applicable Actions`
- `## Risks Or Caveats`
- `## Source Limitations`

`detailed_notes.md` deve includere:

- executive overview breve ma sostanziale;
- mappa dei contenuti;
- copertura estesa per sezioni o temi;
- strumenti citati e contesti d'uso;
- demo e walkthrough con obiettivo, passaggi e risultato;
- domande e risposte del pubblico;
- esempi, caveat, rischi e punti aperti;
- limiti della fonte.

Non deve includere timestamp/minutaggi, non deve copiare la trascrizione e non deve trattare metadata tecnici, log, frontmatter o candidati come contenuto.

## Campi JSON Webinar

Per webinar usare `schemas/webinar_analysis.schema.json`.

Campi richiesti:

- `schema_version`
- `content_type`
- `title`
- `executive_summary`
- `detailed_summary`
- `content_map`
- `key_concepts`
- `tools_mentioned`
- `demos_or_walkthroughs`
- `examples`
- `frameworks_or_models`
- `audience_questions`
- `takeaways`
- `applicable_actions`
- `risks_or_caveats`
- `source_limitations`

## Strumenti Citati

Per ogni strumento citato, quando presente nel transcript, catturare:

- nome;
- descrizione;
- ruolo nel webinar;
- contesto d'uso;
- eventuale demo;
- limiti, vincoli o attenzioni emerse.

Non inventare strumenti. Se il nome e' incerto per qualita' della trascrizione, segnalarlo come `da confermare`.

## Demo O Walkthrough

Per ogni demo o walkthrough, quando presente, catturare:

- cosa viene mostrato;
- obiettivo della demo;
- passaggi principali;
- strumenti usati;
- output o risultato;
- limiti, problemi o caveat emersi.

Non trasformare una semplice citazione di uno strumento in demo se non viene mostrato o descritto un walkthrough.

## Q&A

Per domande del pubblico, catturare:

- domanda o tema della domanda;
- risposta;
- stato: `answered`, `partially_answered` o `open`.

Non aggiungere domande assenti dalla trascrizione.

## Cosa Non Inventare

- Non inventare relatore, titolo, strumenti, framework o demo.
- Non trasformare esempi ipotetici in raccomandazioni operative.
- Non trasformare orientamenti o intenzioni in decisioni confermate.
- Non aggiungere domande del pubblico se non compaiono nella trascrizione.
- Non citare recipe, schema, prompt, report tecnici o candidate glossary come fonte.
- Usa `non rilevato`, `non specificato nella trascrizione`, `non emerso chiaramente` o `da confermare` per informazioni assenti o ambigue.
