# Intelligent Transcript Engine

`intelligent-transcript-engine` trasforma video, audio o trascrizioni in output strutturati:

```text
output/prompts/<nome>_generated_prompt.md
output/markdown/<nome>_summary.md                 per flussi non-webinar
output/markdown/<nome>_detailed_notes.md          per webinar lunghi/round table
output/json/<nome>_classification.json
output/json/<nome>_analysis.json
output/pdf/<nome>_summary.pdf oppure <nome>_detailed_notes.pdf
```

Il progetto separa due parti:

```text
preprocessing deterministico
-> trascrizione, review, normalizzazione, candidati dizionario

workflow agent-driven
-> classificazione, recipe, generated prompt, Markdown primario, analysis JSON
```

Gli script preparano e controllano il materiale. Codex interpreta il contenuto e genera il riassunto strutturato.

## Uso Normale

1. Metti un video in `input/videos/` oppure un audio WAV in `input/audio/`.
2. Chiedi a Codex: `Riassumi questo video usando il workflow del progetto`.
3. Codex esegue la pipeline locale deterministica.
4. Codex usa il transcript selezionato dalla pipeline.
5. Codex genera `generated_prompt.md`, il Markdown primario, `classification.json` e `analysis.json`.
6. Il sistema raccoglie eventuali candidati dizionario da rivedere in futuro.
7. Se richiesto, esporta il Markdown primario in PDF con Pandoc.

Prompt consigliato:

```text
Ho inserito un video in input/videos. Riassumi l'ultimo video usando il workflow del progetto. Esegui prima la pipeline di preprocessing, usa solo il selected_transcript se ready_for_agent_analysis e' true, poi genera il Markdown primario, classification.json e analysis.json. Segnalami eventuali candidati dizionario senza promuoverli automaticamente.
```

Per un file specifico:

```text
Riassumi il video "nome-file.mkv" usando il workflow del progetto. Esegui la pipeline di preprocessing, usa il selected_transcript e genera gli output strutturati. Non trattare report tecnici, candidate glossary o frontmatter come contenuto del video.
```

## Struttura Principale

```text
input/videos/                 video sorgenti
input/audio/                  audio estratti o audio sorgenti

input/transcripts/raw/         trascrizioni grezze
input/transcripts/reviewed/    trascrizioni revisionate/preparate
input/transcripts/normalized/  trascrizioni normalizzate

output/preprocessing/          report tecnici di estrazione audio
output/transcription/          report tecnici di trascrizione
output/review/                 report di review
output/normalization/          report di normalizzazione
output/pipeline/               report della pipeline completa

output/prompts/                generated prompt interni/debug
output/markdown/               Markdown finali leggibili
output/markdown/*_summary.md   summary per flussi non-webinar
output/markdown/*_detailed_notes.md Markdown primario per webinar lunghi
output/json/                   classification e analysis JSON
output/pdf/                    PDF esportati dal Markdown primario

knowledge/global/              regole davvero trasversali
knowledge/work_meetings/       knowledge per tutte le riunioni di lavoro
knowledge/macro_categories/    knowledge per contenuti non-meeting
```

## Pipeline

Quando chiedi a Codex di riassumere un video/audio, il progetto segue questo flusso:

```text
video/audio
-> audio estratto
-> raw transcript
-> quality report
-> reviewed transcript
-> normalized transcript
-> candidate glossary
-> selected transcript
-> workflow agent-driven
-> generated_prompt.md
-> Markdown primario
-> classification.json
-> analysis.json
```

Il runner principale del preprocessing e':

```bash
python3 scripts/run_preprocessing_pipeline.py
```

Coordina gli step deterministici:

```text
Step 1: video/audio -> raw transcript + quality report
Step 2: raw transcript -> reviewed transcript + review report
Step 3: reviewed transcript -> normalized transcript + normalization report
Step 4: raccolta candidati dizionario
Step 5: selezione del transcript migliore
Step 6A: report operativo della pipeline
Step 6B: Codex usa il selected_transcript nel workflow agent-driven
Step 7: export PDF deterministico dal Markdown primario
```

Gli script non invocano Codex CLI e non generano summary/classification/analysis. Questi output finali vengono generati solo dal workflow agent-driven di Codex.
Lo script PDF non genera contenuto: converte solo un Markdown finale gia' esistente in PDF. Per webinar lunghi usa `detailed_notes.md`.

## Riassumere un video con Codex

Metti il video in:

```bash
input/videos/
```

Esempio:

```bash
input/videos/corso-ai.mkv
```

Poi chiedi a Codex:

```text
Riassumi l'ultimo video in input/videos usando il workflow del progetto.
```

Codex deve eseguire:

```bash
python3 scripts/run_preprocessing_pipeline.py --latest-video --context work_meetings --json
```

Se il report contiene `ready_for_agent_analysis: true`, Codex usa `selected_transcript` e genera gli output finali.

## Riassumere Un Audio

Metti l'audio WAV in:

```bash
input/audio/
```

Poi chiedi a Codex:

```text
Ho inserito un audio in input/audio. Riassumilo usando il workflow del progetto.
```

Se vuoi lanciare il runner manualmente su un audio specifico:

```bash
python3 scripts/run_preprocessing_pipeline.py "input/audio/nome-audio.wav" --context work_meetings --json
```

## Runner Preprocessing

Da basename:

```bash
python3 scripts/run_preprocessing_pipeline.py "NOME_BASE" --context work_meetings --json
```

Da video:

```bash
python3 scripts/run_preprocessing_pipeline.py "input/videos/video.mkv" --context work_meetings --json
```

Ultimo video caricato:

```bash
python3 scripts/run_preprocessing_pipeline.py --latest-video --context work_meetings --json
```

Dry run:

```bash
python3 scripts/run_preprocessing_pipeline.py --latest-video --context work_meetings --dry-run --json
```

Output importante:

```json
{
  "pipeline_status": "ready_for_agent_analysis",
  "ready_for_agent_analysis": true,
  "selected_transcript": "input/transcripts/normalized/...",
  "selected_level": "normalized",
  "candidate_count": 3
}
```

Se `ready_for_agent_analysis` e' `true`, Codex puo' generare il riassunto.

Se e' `false`, Codex deve fermarsi, spiegare il motivo operativo e indicare cosa revisionare.

## Trascrizione Batch In Background

Per webinar lunghi, la trascrizione MLX puo' richiedere molto tempo. Quando chiedi a Codex di elaborare nuovi video e mancano ancora i raw transcript, Codex deve avviare solo la trascrizione batch in background e poi fermarsi.

Comando:

```bash
python3 scripts/start_transcription_batch.py
```

Output atteso:

```text
status: started
pid: <PID>
log: output/transcription/transcribe_remaining.log
pending_count: <N>
```

Controllare se il processo e' ancora attivo:

```bash
ps -p <PID> -o pid,etime,pcpu,pmem,command
```

Seguire il log:

```bash
tail -n 40 output/transcription/transcribe_remaining.log
```

Vedere quali audio sono stati trascritti:

```bash
python3 - <<'PY'
from pathlib import Path
for audio in sorted(Path('input/audio').glob('*.wav')):
    raw = Path('input/transcripts/raw') / f'{audio.stem}_raw.md'
    print(('DONE' if raw.exists() else 'TODO'), '|', audio.name)
PY
```

Quando la trascrizione e' terminata, invia a Codex:

```text
La trascrizione batch e' terminata. Prosegui con review, normalizzazione, selezione transcript, generazione detailed_notes/classification/analysis e PDF per i nuovi video completati.
```

## Transcript Usato Per L'Analisi

Il sistema sceglie automaticamente il miglior transcript disponibile:

```text
1. input/transcripts/normalized/<basename>_normalized.md
2. input/transcripts/reviewed/<basename>_reviewed.md
3. input/transcripts/raw/<basename>_raw.md solo se safe_for_analysis = true
```

Non analizzare direttamente il raw se esiste un transcript migliore.

Per verificare la selezione:

```bash
python3 scripts/select_analysis_transcript.py "NOME_BASE" --json
```

## Quando La Pipeline Si Ferma

La pipeline puo' fermarsi se:

```text
- il raw transcript e' tecnicamente sporco;
- safe_for_analysis e' false;
- manca un report tecnico;
- manca un transcript necessario;
- la review manuale e' richiesta;
- il selected transcript non esiste.
```

In questi casi Codex non deve generare il Markdown finale, `classification.json` o `analysis.json`.

## Output Finali

Il workflow agent-driven produce:

```text
output/prompts/<nome>_generated_prompt.md
output/markdown/<nome>_summary.md          per flussi non-webinar
output/markdown/<nome>_detailed_notes.md   unico Markdown per webinar lunghi/round table
output/json/<nome>_classification.json
output/json/<nome>_analysis.json
```

Significato:

```text
generated_prompt.md       artefatto interno/debug
summary.md                riassunto leggibile per flussi non-webinar
detailed_notes.md         documento primario per webinar lunghi, demo, round table o Q&A
classification.json       classificazione type/subtype/recipe/context
analysis.json             analisi strutturata in JSON
```

Il file principale da leggere e':

```text
output/markdown/<nome>_summary.md          per flussi non-webinar
output/markdown/<nome>_detailed_notes.md   per webinar lunghi/round table
```

## Export PDF

Lo Step 7 converte un Markdown finale gia' generato in PDF usando Pandoc.

Dipendenze richieste:

```bash
pandoc --version
xelatex --version
```

Lo script non installa dipendenze, non invoca Codex CLI e non modifica il contenuto del Markdown sorgente.

Uso da path diretto:

```bash
python3 scripts/export_summary_pdf.py "output/markdown/NOME_BASE_summary.md" --output-dir "output/pdf"
python3 scripts/export_summary_pdf.py "output/markdown/NOME_BASE_detailed_notes.md" --output-dir "output/pdf"
```

Uso da basename, secondo la convenzione reale `output/markdown/<basename>_detailed_notes.md` se presente, altrimenti `output/markdown/<basename>_summary.md`:

```bash
python3 scripts/export_summary_pdf.py "NOME_BASE" --output-dir "output/pdf"
```

Output:

```text
output/pdf/<basename>_summary.pdf
output/pdf/<basename>_detailed_notes.pdf   quando la sorgente e' detailed_notes.md
```

Opzioni utili:

```bash
python3 scripts/export_summary_pdf.py "NOME_BASE" --output-dir "output/pdf" --force --json
python3 scripts/export_summary_pdf.py "NOME_BASE" --output-dir "output/pdf" --toc
python3 scripts/export_summary_pdf.py "NOME_BASE" --output-dir "output/pdf" --output-name "riassunto.pdf"
```

Quando l'utente chiede "genera anche il PDF", Codex deve prima generare gli output agent-driven e poi eseguire:

```bash
python3 scripts/export_summary_pdf.py "<path/to/markdown-finale.md>" --output-dir "output/pdf"
```

Per webinar lunghi o round table, il path deve puntare a `detailed_notes.md`, non a `summary.md`.

## Regole Per Un Markdown Finale Pulito

Il Markdown finale deve basarsi solo sul transcript selezionato.

Non deve trattare come contenuto del video:

```text
quality_warnings
normalization_candidates
review report
normalization report
pipeline report
candidate files
frontmatter tecnico
log tecnici
regole del progetto
```

Questi sono operational metadata.

Il Markdown finale deve:

```text
- non inventare;
- non inserire minutaggi;
- distinguere decisioni confermate, ipotesi, proposte e punti aperti;
- usare "non specificato nella trascrizione" quando un dato manca;
- usare "da confermare" quando qualcosa e' ambiguo;
- considerare decisione confermata solo cio' che e' esplicito nel transcript.
```

## Webinar Lunghi

Per contenuti classificati come `type: webinar` con `selected_recipe: recipes/webinar.md`, il workflow non deve comprimere tutto nella struttura generic.

Per webinar lunghi, round table, demo, Q&A o contenuti con molti strumenti:

```text
detailed_notes.md   unico Markdown finale e documento principale
analysis.json       struttura webinar-specific secondo schemas/webinar_analysis.schema.json
```

Non generare o aggiornare `summary.md` per webinar lunghi o round table. Se `summary.md` esiste da una run precedente, considerarlo legacy/stale.

`detailed_notes.md` deve essere abbastanza ricco da sostituire sia il vecchio summary sia le vecchie note estese. Deve separare almeno:

```text
executive overview
content map
detailed thematic sections
key concepts
tools/platforms/assets mentioned
demo or walkthrough notes
examples
frameworks or models
audience questions
takeaways
applicable actions
risks or caveats
source limitations
```

Se un output webinar risulta troppo scarno, verificare:

```text
recipe scelta
generated_prompt.md
rapporto parole transcript/detailed_notes.md
assenza di aggiornamenti a summary.md
schema usato in analysis.json
```

## Context Knowledge

Il parametro `--context` decide quale knowledge base usare.

Default consigliato per riunioni/call/progetti di lavoro:

```bash
--context work_meetings
```

Da usare per:

```text
riunioni tecniche
call di progetto
flussi applicativi
riunioni operative
discussioni IMU/TARI/SIGE
```

Contenuti finance:

```bash
--context macro_categories/finance
```

Contenuti travel:

```bash
--context macro_categories/travel
```

Contenuti social media management:

```bash
--context macro_categories/social_media_management
```

Contenuti generici non-meeting:

```bash
--context macro_categories/generic
```

Non creare sottocategorie granulari. Una riunione TARI e una riunione IMU vanno entrambe in:

```text
knowledge/work_meetings/
```

`knowledge/global/` contiene solo termini e regole davvero trasversali.

## Gestione Parole Da Correggere

Il progetto distingue tre livelli:

```text
candidate
approved term
normalization rule
```

### Candidate

Un candidate e' un suggerimento.

Esempio:

```text
Copario Chat -> Copilot Chat
```

Non viene applicato automaticamente.

I candidate stanno in:

```text
knowledge/work_meetings/candidates/
knowledge/macro_categories/<categoria>/candidates/
```

### Approved Term

Un approved term e' un termine canonico approvato.

File:

```text
knowledge/<context>/approved_terms.yml
```

Serve come glossario.

### Normalization Rule

Una normalization rule e' una regola approvata che viene applicata automaticamente alla trascrizione normalizzata.

File:

```text
knowledge/<context>/normalization_rules.yml
```

Esempio:

```yaml
rules:
  - id: copilot_chat_from_copario_chat
    enabled: true
    observed:
      - "Copario Chat"
    canonical: "Copilot Chat"
    match: "phrase"
    case_sensitive: false
```

Solo le regole in `normalization_rules.yml` vengono applicate automaticamente.

## Candidati: Comandi

La pipeline Step 6A raccoglie gia' i candidati automaticamente.

Raccogliere manualmente:

```bash
python3 scripts/manage_candidates.py collect "NOME_BASE" --context work_meetings --json
```

Dry run:

```bash
python3 scripts/manage_candidates.py collect "NOME_BASE" --context work_meetings --dry-run --json
```

Listare:

```bash
python3 scripts/manage_candidates.py list --context work_meetings
```

Listare in JSON:

```bash
python3 scripts/manage_candidates.py list --context work_meetings --json
```

Promuovere a regola di normalizzazione:

```bash
python3 scripts/manage_candidates.py promote \
  --context work_meetings \
  --candidate-id cand_xxxxx \
  --to normalization_rules
```

Promuovere ad approved term:

```bash
python3 scripts/manage_candidates.py promote \
  --context work_meetings \
  --candidate-id cand_xxxxx \
  --to approved_terms
```

Rifiutare:

```bash
python3 scripts/manage_candidates.py reject \
  --context work_meetings \
  --candidate-id cand_xxxxx \
  --notes "Motivo del rifiuto"
```

Regola fondamentale:

```text
candidate != approved
```

I candidati non vengono promossi automaticamente: il sistema non promuove nulla automaticamente.

## Applicare Una Nuova Regola Al Video Corrente

Se promuovi un candidato dopo aver gia' generato il normalized transcript, devi rigenerare la normalizzazione:

```bash
python3 scripts/normalize_transcript.py "NOME_BASE" --context work_meetings --force
```

Poi rilancia il runner:

```bash
python3 scripts/run_preprocessing_pipeline.py "NOME_BASE" --context work_meetings --json
```

Infine chiedi a Codex:

```text
Ho aggiornato le regole di normalizzazione. Rigenera l'output finale usando il workflow del progetto e il transcript selezionato dalla pipeline.
```

## Flusso Consigliato Per Migliorare La Base Parole

Dopo ogni video:

```text
1. genera l'output finale normalmente;
2. guarda i candidati raccolti;
3. promuovi solo quelli sicuri;
4. rifiuta quelli sbagliati;
5. lascia in candidate quelli dubbi;
6. rigenera la normalizzazione solo se vuoi aggiornare anche il video corrente.
```

Le nuove regole approvate verranno usate nelle normalizzazioni successive.

## Esempio: Video Di Una Riunione

1. Copia il video:

```bash
cp "/percorso/video-riunione.mkv" input/videos/
```

2. Chiedi a Codex:

```text
Riassumi l'ultimo video in input/videos usando il workflow del progetto.
```

Codex deve:

```text
- eseguire run_preprocessing_pipeline.py;
- usare selected_transcript;
- generare generated_prompt.md;
- generare il Markdown primario;
- generare classification.json;
- generare analysis.json;
- segnalare eventuali candidati dizionario senza promuoverli.
```

## Esempio: Video Finance

1. Copia il video:

```bash
cp "/percorso/video-finanza.mp4" input/videos/
```

2. Chiedi a Codex:

```text
Riassumi l'ultimo video in input/videos. E' un contenuto finance, quindi usa il context macro_categories/finance.
```

Codex usera':

```bash
python3 scripts/run_preprocessing_pipeline.py --latest-video --context macro_categories/finance --json
```

Poi generera' l'output strutturato.

## Comandi Utili

Runner completo:

```bash
python3 scripts/run_preprocessing_pipeline.py "NOME_BASE" --context work_meetings --json
```

Dry run:

```bash
python3 scripts/run_preprocessing_pipeline.py "NOME_BASE" --context work_meetings --dry-run --json
```

Ultimo video:

```bash
python3 scripts/run_preprocessing_pipeline.py --latest-video --context work_meetings --json
```

Selezionare transcript:

```bash
python3 scripts/select_analysis_transcript.py "NOME_BASE" --json
```

Normalizzare:

```bash
python3 scripts/normalize_transcript.py "NOME_BASE" --context work_meetings
```

Raccogliere candidati:

```bash
python3 scripts/manage_candidates.py collect "NOME_BASE" --context work_meetings --json
```

Listare candidati:

```bash
python3 scripts/manage_candidates.py list --context work_meetings
```

Esportare il Markdown finale in PDF:

```bash
python3 scripts/export_summary_pdf.py "NOME_BASE" --output-dir "output/pdf"
```

## Checklist Veloce

```text
[ ] Metto video/audio in input/videos/ o input/audio/
[ ] Chiedo a Codex: "Riassumi questo video"
[ ] Codex esegue run_preprocessing_pipeline.py
[ ] La pipeline restituisce ready_for_agent_analysis = true
[ ] Codex usa selected_transcript
[ ] Codex genera generated_prompt.md, Markdown primario, classification.json, analysis.json
[ ] Per webinar lunghi il Markdown primario e' output/markdown/<nome>_detailed_notes.md
[ ] Se richiesto, Codex esporta il Markdown primario in PDF
[ ] Controllo eventuali candidati dizionario
[ ] Promuovo solo correzioni sicure
```

## Regole Importanti

- Non chiedere a Codex di analizzare direttamente `input/transcripts/raw/...`.
- Usare sempre il transcript selezionato dalla pipeline.
- Non promuovere automaticamente i candidati.
- Non mettere metadata tecnici nel summary.
- Non usare `knowledge/global/` per tutto.
- Le riunioni di lavoro usano `knowledge/work_meetings/`.

## Stato Attuale

Pipeline locale implementata fino a Step 6B:

```text
video/audio
-> preprocessing deterministico
-> selected_transcript
-> workflow agent-driven Codex
-> generated_prompt.md / Markdown primario / classification.json / analysis.json
-> PDF dal Markdown primario solo se richiesto
```

Nessuno script deterministico invoca Codex CLI. I candidati restano suggerimenti finche' non vengono promossi manualmente.
