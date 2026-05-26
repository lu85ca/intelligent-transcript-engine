# Regole operative per Codex

Questo progetto analizza trascrizioni testuali con un workflow agent-driven. Codex legge trascrizione, regole, skill, recipe, template, schemi e knowledge context, poi genera direttamente prompt di debug, output Markdown e output JSON.

Il progetto puo' avere una pipeline locale di preprocessing video/audio basata su MLX Whisper large-v3-turbo. Questa pipeline deve restare deterministica e script-driven: prepara audio, trascrizione, normalizzazioni conservative e log tecnici. Classificazione, scelta recipe, generated prompt, summary, classification JSON e analysis JSON restano agent-driven.

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
- Le istruzioni di progetto, skill, recipe, template, schema, domain profile, knowledge context, registry, glossari, dizionari, regole di normalizzazione, candidati, esempi e prompt generato sono `operational metadata`: servono a guidare il lavoro dell’agente, non sono contenuto della trascrizione.
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

## Pipeline locale video/audio

La pipeline di preprocessing video/audio deve seguire questi confini:

- estrazione audio, trascrizione e normalizzazione conservativa sono preprocessing deterministico/script-driven;
- il modello di trascrizione previsto e' MLX Whisper large-v3-turbo;
- gli script preparano input e log tecnici;
- gli script non analizzano semanticamente il contenuto;
- gli script di preprocessing non invocano Codex;
- eventuali script di orchestrazione del workflow che invocano Codex CLI devono essere introdotti solo in uno step dedicato e richiesto esplicitamente;
- non aggiungere watcher automatici;
- non aggiungere API esterne non richieste;
- la classificazione e l'analisi finale restano agent-driven.

I file generati dal preprocessing, inclusi frontmatter della trascrizione raw e log tecnici in `output/preprocessing/` e `output/transcription/`, sono operational metadata. Anche campi tecnici come `quality_warnings`, `normalization_candidates` e `safe_for_analysis` sono operational metadata: possono aiutare tracciabilita', debug e decisioni operative sulla qualita' dell'input, ma non devono finire come contenuto in `summary.md` o `analysis.json`. Il workflow agent-driven inizia dalla trascrizione testuale preparata e deve continuare a distinguere contenuto sorgente e metadati tecnici. I warning tecnici non devono essere trattati come fatti del webinar o della riunione.

Se esiste una versione in `input/transcripts/reviewed/`, il workflow agent-driven deve preferire quella alla trascrizione raw corrispondente. Se il JSON tecnico di trascrizione indica `safe_for_analysis: false`, non usare direttamente il raw transcript per produrre summary o analysis finali: preparare prima una versione reviewed. I report in `output/review/` e il frontmatter dei transcript reviewed sono operational metadata e input preparatori, non fatti del contenuto.

## Knowledge incrementale

La conoscenza incrementale vive in `knowledge/` ed e' operational metadata.

Struttura:

- `knowledge/global/`: solo termini, regole e contesto davvero trasversali.
- `knowledge/work_meetings/`: unico contesto incrementale per tutte le riunioni di lavoro.
- `knowledge/macro_categories/finance/`: contenuti non-meeting di finanza.
- `knowledge/macro_categories/travel/`: contenuti non-meeting di viaggio.
- `knowledge/macro_categories/social_media_management/`: contenuti non-meeting di social media management.
- `knowledge/macro_categories/generic/`: fallback per contenuti non-meeting senza categoria chiara.
- `knowledge/registry.yml`: registry dei contesti, regole di selezione e routing dei candidati.

Regole di selezione:

- caricare sempre `knowledge/global/`;
- per ogni riunione di lavoro, inclusi meeting generici e technical flow meeting, caricare `knowledge/work_meetings/`;
- riunioni su IMU, TARI, SIGE, flussi documentali, database, rilasci o temi tecnici/funzionali generici alimentano sempre `knowledge/work_meetings/`;
- non creare sottocartelle di knowledge per IMU, TARI, SIGE, Libra, STARDAS, DoQui Acta o domini applicativi simili;
- termini come IMU, TARI, SIGE, Libra, STARDAS e DoQui Acta, se approvati, devono stare nel contesto unico `knowledge/work_meetings/`;
- per contenuti non-meeting, scegliere una sola macro-categoria se chiara; altrimenti usare `knowledge/macro_categories/generic/`;
- i candidati vanno salvati nella cartella `candidates/` del contesto selezionato;
- nessun candidato deve essere promosso automaticamente ad approved term;
- la promozione dei candidati resta manuale.

I file `approved_terms.yml`, `normalization_rules.yml`, `context.md`, `candidates/`, `examples/` e `registry.yml` possono guidare normalizzazione e analisi, ma non devono mai comparire nel summary o in `analysis.json` come contenuto della riunione o del video.

## Classificazione meeting

Per i meeting, Codex deve distinguere:

- `type: meeting`, `subtype: generic_meeting`: riunione generica con decisioni, action item, follow-up o coordinamento.
- `type: meeting`, `subtype: technical_flow_meeting`: riunione tecnica/funzionale in cui l'obiettivo è ricostruire un flusso applicativo end-to-end, sistemi coinvolti, stati, componenti, integrazioni, decisioni, punti aperti e attività operative.

Per le riunioni di lavoro, la conoscenza incrementale deve essere selezionata dal contesto unico `knowledge/work_meetings/`, indipendentemente dal dominio specifico discusso. Non creare nuovi domain profile o nuove cartelle knowledge granulari per singoli domini applicativi.

I domain profile eventualmente esistenti restano operational metadata e non devono introdurre informazioni assenti dalla trascrizione. Le normalizzazioni devono essere motivate solo con evidenze testuali della trascrizione, non citando domain profile o knowledge context come supporto.

## Separazione contenuto e regole

Codex deve distinguere sempre tra:

- `source content`: ciò che è effettivamente presente nella trascrizione;
- `operational metadata`: regole del progetto, istruzioni della skill, recipe, template, schema, domain profile, knowledge context, registry, glossari, dizionari, regole di normalizzazione, candidati, esempi, prompt generato e convenzioni di output.

Solo il `source content` può alimentare fatti, decisioni, ipotesi, orientamenti, azioni, rischi, follow-up e punti aperti della riunione.

Gli `operational metadata` guidano l’analisi ma non sono contenuto della riunione o del video. Non devono comparire come fatti, interpretazioni, decisioni, ipotesi, orientamenti, attività operative, punti aperti, rischi o follow-up.

Sono vietate nei contenuti finali formule come: "supportato dal domain profile", "supportato dal knowledge context", "secondo la recipe", "in base allo schema", "in base al registry", "come indicato nel generated prompt" o "seguendo le istruzioni del workflow".

Una normalizzazione può essere dichiarata solo in termini di evidenza testuale. Esempio corretto: "La normalizzazione di Stardus/Stardust come STARDAS è supportata dai riferimenti ripetuti al sistema documentale nella trascrizione." Esempio non corretto: "La normalizzazione è supportata dal domain profile." Esempio non corretto: "La normalizzazione è supportata dal knowledge context."

Se un dominio applicativo, per esempio SIGE IMU, non è esplicitato nella trascrizione, non inserirlo in `analysis.json` come interpretazione del contenuto. Può restare solo come `selected_domain_profile` in `classification.json`.

`generated_prompt.md` è un artefatto interno/debug per tracciabilità e riproducibilità del workflow. Non è un output finale destinato al lettore e non deve essere trattato come fonte informativa primaria.

Regole come “non inserire minutaggi”, “non inventare informazioni”, “produrre Markdown e JSON”, “usare non rilevato”, “salvare generated_prompt.md”, “seguire la recipe”, “selezionare il domain profile” o “selezionare il knowledge context” devono restare regole di processamento e non devono mai essere riportate come contenuto della riunione o del video.

Le decisioni confermate devono essere più restrittive: una voce può essere classificata come decisione confermata solo se nella trascrizione c’è accordo esplicito o una formulazione chiaramente decisionale. In caso contrario, classificarla come orientamento tecnico, ipotesi emersa, proposta non confermata o punto aperto.

In assenza di evidenza esplicita, preferire sempre una categoria meno forte: orientamento tecnico, ipotesi emersa, proposta non confermata o punto aperto.

Prima di salvare `summary.md` e `analysis.json`, Codex deve fare un controllo qualità specifico:

- cercare nel summary e nel JSON eventuali frasi che derivano da regole operative, istruzioni di progetto o metadati del workflow;
- se presenti, rimuoverle dai contenuti della riunione;
- verificare che `interpretations` e normalizzazioni non citino recipe, domain profile, knowledge context, registry, skill, schema, template, generated prompt o workflow come fonte;
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
6. Selezionare il knowledge context seguendo `knowledge/registry.yml`.
7. Per riunioni di lavoro, usare sempre `knowledge/global/` e `knowledge/work_meetings/`.
8. Per contenuti non-meeting, usare `knowledge/global/` e una macro-categoria in `knowledge/macro_categories/`, oppure `generic` come fallback.
9. Se strettamente pertinente e gia' previsto dal progetto, scegliere un domain profile da `domain_profiles/` e dichiararlo nella classification; non creare nuovi domain profile granulari.
10. Leggere `prompt_templates/meta_prompt.md` e `prompt_templates/final_analysis_prompt.md`.
11. Generare un prompt ottimizzato per la trascrizione specifica.
12. Salvare il prompt in `output/prompts/<nome>_generated_prompt.md`.
13. Applicare il prompt alla trascrizione.
14. Salvare la classificazione in `output/json/<nome>_classification.json`.
15. Salvare l'analisi strutturata in `output/json/<nome>_analysis.json`.
16. Salvare il riepilogo leggibile in `output/markdown/<nome>_summary.md`.
17. Fare un controllo qualita' finale su completezza, tracciabilita', assenza di invenzioni e rispetto degli schemi.

## Output atteso

Per `input/transcripts/example.md`, quando richiesto, Codex deve produrre:

- `output/prompts/example_generated_prompt.md`
- `output/markdown/example_summary.md`
- `output/json/example_analysis.json`
- `output/json/example_classification.json`
