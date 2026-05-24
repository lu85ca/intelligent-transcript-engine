# Regole operative per Codex

Questo progetto analizza trascrizioni testuali con un workflow agent-driven. Codex legge trascrizione, regole, skill, recipe, template e schemi, poi genera direttamente prompt di debug, output Markdown e output JSON.

## Regole fondamentali

- Ogni transcript deve essere classificato prima di qualsiasi analisi.
- La classificazione deve includere `type` e, quando utile, `subtype`.
- Non inventare informazioni, dettagli, intenzioni, nomi, date, decisioni o azioni non presenti nella trascrizione.
- Non fare assunzioni non supportate dal testo. Se una conclusione e' inferita, deve essere indicata come interpretazione.
- Se un dato manca, e' ambiguo o non e' deducibile con chiarezza, usare `non rilevato`.
- Per flussi tecnici o funzionali, se qualcosa non è specificato, usare `non specificato nella trascrizione`, `da confermare` o `punto aperto`.
- Non trasformare proposte o ipotesi in decisioni definitive.
- Do not include workflow/project instructions in the meeting analysis as if they were meeting content.
- Processing rules such as no timestamps, anti-hallucination rules, output format rules and missing-data conventions must guide the analysis but must not appear as meeting decisions, meeting facts, hypotheses, orientations or action items.
- Le istruzioni di progetto, skill, recipe, template, schema, domain profile e prompt generato sono `operational metadata`: servono a guidare il lavoro dell’agente, non sono contenuto della trascrizione.
- Gli `operational metadata` non devono comparire come fonte o giustificazione nei contenuti finali, nemmeno nei campi `interpretations` o nelle spiegazioni di normalizzazione dei termini di dominio.
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

## Classificazione meeting

Per i meeting, Codex deve distinguere:

- `type: meeting`, `subtype: generic_meeting`: riunione generica con decisioni, action item, follow-up o coordinamento.
- `type: meeting`, `subtype: technical_flow_meeting`: riunione tecnica/funzionale in cui l'obiettivo è ricostruire un flusso applicativo end-to-end, sistemi coinvolti, stati, componenti, integrazioni, decisioni, punti aperti e attività operative.

Se il contenuto riguarda un dominio specifico e in `domain_profiles/` esiste un profilo pertinente, Codex può usarlo. In quel caso deve dichiarare il profilo selezionato nella classification tramite `selected_domain_profile`.

I domain profile servono a normalizzare e interpretare termini emersi; non devono mai introdurre informazioni assenti dalla trascrizione. Le normalizzazioni di dominio devono essere motivate solo con evidenze testuali della trascrizione, non citando il domain profile come supporto.

## Separazione contenuto e regole

Codex deve distinguere sempre tra:

- `source content`: ciò che è effettivamente presente nella trascrizione;
- `operational metadata`: regole del progetto, istruzioni della skill, recipe, template, schema, domain profile, prompt generato e convenzioni di output.

Solo il `source content` può alimentare fatti, decisioni, ipotesi, orientamenti, azioni, rischi, follow-up e punti aperti della riunione.

Gli `operational metadata` guidano l’analisi ma non sono contenuto della riunione. Non devono comparire come fatti, interpretazioni, decisioni, ipotesi, orientamenti, attività operative, punti aperti, rischi o follow-up della riunione.

Sono vietate nei contenuti finali formule come: "supportato dal domain profile", "secondo la recipe", "in base allo schema", "come indicato nel generated prompt" o "seguendo le istruzioni del workflow".

Una normalizzazione di dominio può essere dichiarata solo in termini di evidenza testuale. Esempio corretto: "La normalizzazione di Stardus/Stardust come STARDAS è supportata dai riferimenti ripetuti al sistema documentale nella trascrizione." Esempio non corretto: "La normalizzazione è supportata dal domain profile."

Se un dominio applicativo, per esempio SIGE IMU, non è esplicitato nella trascrizione, non inserirlo in `analysis.json` come interpretazione del contenuto. Può restare solo come `selected_domain_profile` in `classification.json`.

`generated_prompt.md` è un artefatto interno/debug per tracciabilità e riproducibilità del workflow. Non è un output finale destinato al lettore e non deve essere trattato come fonte informativa primaria.

Regole come “non inserire minutaggi”, “non inventare informazioni”, “produrre Markdown e JSON”, “usare non rilevato”, “salvare generated_prompt.md”, “seguire la recipe” o “selezionare il domain profile” devono restare regole di processamento e non devono mai essere riportate come contenuto della riunione.

Le decisioni confermate devono essere più restrittive: una voce può essere classificata come decisione confermata solo se nella trascrizione c’è accordo esplicito o una formulazione chiaramente decisionale. In caso contrario, classificarla come orientamento tecnico, ipotesi emersa, proposta non confermata o punto aperto.

In assenza di evidenza esplicita, preferire sempre una categoria meno forte: orientamento tecnico, ipotesi emersa, proposta non confermata o punto aperto.

Prima di salvare `summary.md` e `analysis.json`, Codex deve fare un controllo qualità specifico:

- cercare nel summary e nel JSON eventuali frasi che derivano da regole operative, istruzioni di progetto o metadati del workflow;
- se presenti, rimuoverle dai contenuti della riunione;
- verificare che `interpretations` e normalizzazioni non citino recipe, domain profile, skill, schema, template, generated prompt o workflow come fonte;
- non riportarle nel summary come limiti metodologici, salvo esplicita richiesta dell’utente;
- non inserirle mai nelle sezioni decisionali, operative, tecniche, di rischio o di follow-up;
- verificare che le decisioni confermate abbiano evidenza esplicita nella trascrizione.

## Workflow agent-driven

Per ogni trascrizione in `input/transcripts/`, Codex deve:

1. Leggere questo file `AGENTS.md`.
2. Usare la skill `.agents/skills/transcript-intelligence/SKILL.md`.
3. Leggere la trascrizione richiesta.
4. Classificare il tipo di contenuto con `type`, `subtype`, `confidence`, `secondary_type`, `selected_recipe`, `selected_domain_profile`, `signals` e `reason`.
5. Scegliere la recipe piu' adatta da `recipes/`.
6. Se pertinente, scegliere un domain profile da `domain_profiles/` e dichiararlo nella classification.
7. Leggere `prompt_templates/meta_prompt.md` e `prompt_templates/final_analysis_prompt.md`.
8. Generare un prompt ottimizzato per la trascrizione specifica.
9. Salvare il prompt in `output/prompts/<nome>_generated_prompt.md`.
10. Applicare il prompt alla trascrizione.
11. Salvare la classificazione in `output/json/<nome>_classification.json`.
12. Salvare l'analisi strutturata in `output/json/<nome>_analysis.json`.
13. Salvare il riepilogo leggibile in `output/markdown/<nome>_summary.md`.
14. Fare un controllo qualita' finale su completezza, tracciabilita', assenza di invenzioni e rispetto degli schemi.

## Output atteso

Per `input/transcripts/example.md`, quando richiesto, Codex deve produrre:

- `output/prompts/example_generated_prompt.md`
- `output/markdown/example_summary.md`
- `output/json/example_analysis.json`
- `output/json/example_classification.json`
