# Intelligent Transcript Engine

`intelligent-transcript-engine` e' un progetto agent-driven per analizzare file di trascrizione testuale, con una futura pipeline locale di preprocessing video/audio.

L'obiettivo e' far lavorare Codex come agente: leggere regole, skill, recipe, template e trascrizione, classificare il contenuto, generare un prompt ottimizzato e produrre output Markdown e JSON.

Il progetto non usa piu' uno script Python come pipeline principale. Codex/AI e' responsabile di classificare, scegliere la recipe, generare il prompt, applicarlo e salvare gli output.

Il preprocessing video/audio, quando implementato, deve restare locale e script-driven: estrazione audio, trascrizione con MLX Whisper large-v3-turbo, normalizzazione conservativa e log tecnici. Gli script di preprocessing non devono analizzare semanticamente il contenuto e non devono invocare Codex.

## Struttura

- `AGENTS.md`: regole operative per Codex e per gli agenti che lavorano sul progetto.
- `input/transcripts/`: trascrizioni sorgenti da analizzare.
- `input/videos/`: video sorgenti per la pipeline raw video/audio.
- `input/audio/`: audio WAV estratto dai video.
- `input/transcripts/raw/`: trascrizioni grezze prodotte da MLX Whisper.
- `output/markdown/`: risultati leggibili in Markdown.
- `output/json/`: risultati strutturati in JSON.
- `output/prompts/`: prompt generati per debug e riproducibilita'.
- `output/preprocessing/`: log tecnici di estrazione audio.
- `output/transcription/`: log tecnici di trascrizione raw.
- `prompt_templates/`: template per generare e applicare prompt di analisi.
- `recipes/`: istruzioni di analisi per tipo di contenuto.
- `schemas/`: schemi JSON per classificazione e output.
- `knowledge/`: contesti incrementali, glossari, regole conservative, candidati ed esempi.
- `examples/`: esempi e materiale dimostrativo.
- `.agents/skills/transcript-intelligence/`: skill locale dedicata alla transcript intelligence.

## Knowledge context

La knowledge incrementale e' operational metadata: puo' guidare normalizzazione e analisi, ma non deve comparire come contenuto negli output finali.

- `knowledge/global/`: termini e regole davvero trasversali.
- `knowledge/work_meetings/`: unico contesto per tutte le riunioni di lavoro, incluse IMU, TARI, SIGE, flussi documentali, database, rilasci e riunioni tecnico/funzionali generiche.
- `knowledge/macro_categories/finance/`: contenuti non-meeting di finanza.
- `knowledge/macro_categories/travel/`: contenuti non-meeting di viaggio.
- `knowledge/macro_categories/social_media_management/`: contenuti non-meeting di social media management.
- `knowledge/macro_categories/generic/`: fallback per contenuti non-meeting.
- `knowledge/registry.yml`: regole di selezione dei contesti.

I candidati vanno nella cartella `candidates/` del contesto selezionato e non vengono mai promossi automaticamente.

## Pipeline raw video/audio

Step 1 prepara trascrizioni grezze da video locali. Non invoca Codex, non classifica, non normalizza e non produce summary o JSON di analisi.

Dipendenze richieste:

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install mlx-whisper
```

Nota: nell'ambiente corrente `ffmpeg` e' disponibile, mentre `mlx_whisper` deve essere installato nel venv prima della trascrizione.

Uso:

```bash
cp "/path/al/video.mp4" input/videos/
scripts/process_videos.sh
```

Rigenerare sovrascrivendo output esistenti:

```bash
scripts/process_videos.sh --force
```

Senza `--force`, una trascrizione raw gia' esistente non viene ritrascritta e un eventuale report tecnico gia' presente viene mantenuto. Con `--force`, trascrizione e report tecnico vengono rigenerati completamente.

Test con un singolo video/audio:

```bash
cp "/path/al/video.mp4" input/videos/
scripts/prepare_video_inputs.sh
source .venv/bin/activate
python3 scripts/transcribe_audio_mlx.py input/audio/<basename>.wav
```

Output prodotti:

- `input/audio/<basename>.wav`
- `input/transcripts/raw/<basename>_raw.md`
- `output/preprocessing/<basename>_preprocessing.json`
- `output/transcription/<basename>_transcription.json`

I metadati frontmatter delle trascrizioni raw e i log JSON tecnici sono operational metadata: servono per tracciabilita' e debug, non come contenuto da riportare negli output finali.

Per webinar lunghi o audio rumorosi, il JSON tecnico in `output/transcription/` puo' includere:

- `quality_warnings`: warning tecnici su possibili loop, ripetizioni iniziali/finali o altri segnali di trascrizione sporca.
- `normalization_candidates`: possibili termini sospetti da rivedere manualmente, senza sostituzione automatica.
- `safe_for_analysis`: `false` quando la trascrizione raw dovrebbe essere revisionata prima di lanciare il workflow agent-driven.

Questi campi non sono analisi del contenuto e non devono essere riportati in `summary.md` o `analysis.json`. Le correzioni automatiche e la normalizzazione saranno gestite in uno step successivo.

Controllo manuale per verificare che un report tecnico ricco non venga svuotato da una run senza `--force`:

```bash
python3 scripts/transcribe_audio_mlx.py input/audio/<basename>.wav
```

## Reviewed transcripts

Quando `output/transcription/<basename>_transcription.json` contiene `safe_for_analysis: false`, il raw transcript non dovrebbe essere usato direttamente dal workflow agent-driven. Preparare prima una versione reviewed in `input/transcripts/reviewed/`.

Differenza:

- `input/transcripts/raw/`: output grezzo di MLX Whisper, invariato.
- `input/transcripts/reviewed/`: copia revisionabile con frontmatter aggiornato ed eventuale safe cleanup tecnico.
- `output/review/`: report tecnico della review.

Creare un reviewed draft conservativo, senza rimuovere o correggere testo:

```bash
python3 scripts/prepare_review_transcript.py input/transcripts/raw/<basename>_raw.md
```

Applicare safe cleanup opzionale su ripetizioni tecniche evidenti:

```bash
python3 scripts/prepare_review_transcript.py input/transcripts/raw/<basename>_raw.md --apply-safe-cleanup
```

La normalizzazione conservativa e' implementata nello Step 3 e applica solo regole approvate in `normalization_rules.yml`. I `normalization_candidates` vengono riportati nel report di review ma non modificano il transcript, non aggiornano `knowledge/` e non vengono promossi automaticamente.

## Normalized transcripts

Step 3 parte da un transcript reviewed e produce una versione normalizzata usando solo regole approvate in `knowledge/*/normalization_rules.yml`.

Input e output:

- input: `input/transcripts/reviewed/<basename>_reviewed.md`
- output: `input/transcripts/normalized/<basename>_normalized.md`
- report tecnico: `output/normalization/<basename>_normalization.json`

Esempio:

```bash
python3 scripts/normalize_transcript.py "<basename>" --context work_meetings
```

Dry run senza scrivere file:

```bash
python3 scripts/normalize_transcript.py "<basename>" --context work_meetings --dry-run
```

Rigenerare output esistenti:

```bash
python3 scripts/normalize_transcript.py "<basename>" --context work_meetings --force
```

La normalizzazione e' conservativa: applica solo regole `enabled` approvate, non usa `normalization_candidates`, non aggiorna `knowledge/`, non corregge grammatica, non riscrive frasi e non classifica il contenuto. Il normalization report e' operational metadata e non deve essere riportato come contenuto in `summary.md` o `analysis.json`.

## Selezione transcript per analisi

Prima del workflow agent-driven, usare la policy Step 5 per scegliere il transcript migliore disponibile:

1. `input/transcripts/normalized/<basename>_normalized.md`
2. `input/transcripts/reviewed/<basename>_reviewed.md`
3. `input/transcripts/raw/<basename>_raw.md`, solo se `output/transcription/<basename>_transcription.json` contiene `safe_for_analysis: true`

Comando:

```bash
python3 scripts/select_analysis_transcript.py "<basename>"
```

Output JSON tecnico:

```bash
python3 scripts/select_analysis_transcript.py "<basename>" --json
```

Se la policy restituisce `requires_review`, il raw transcript non deve essere analizzato direttamente: creare o verificare prima una versione reviewed. Il JSON di selezione, i quality warning, i candidati e i report tecnici sono operational metadata, non contenuto da riportare negli output finali.

## Flusso agent-driven

1. Inserire o preparare una trascrizione in `input/transcripts/`.
2. Codex legge `AGENTS.md`.
3. Codex usa `.agents/skills/transcript-intelligence/SKILL.md`.
4. Codex seleziona il transcript di analisi con `scripts/select_analysis_transcript.py`.
5. Se la policy richiede review, Codex si ferma e non produce summary finale.
6. Codex classifica la trascrizione selezionata.
7. Codex sceglie la recipe piu' adatta da `recipes/`.
8. Codex seleziona i knowledge context tramite `knowledge/registry.yml`.
9. Codex usa i template in `prompt_templates/` per generare un prompt ottimizzato.
10. Codex salva il prompt in `output/prompts/<nome>_generated_prompt.md`.
11. Codex applica il prompt alla trascrizione selezionata.
12. Codex salva:
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
- non trattare i file in `knowledge/` come contenuto della trascrizione;
- non promuovere automaticamente candidati ad approved term;
- non aggiungere dipendenze o API esterne; gli script di preprocessing non devono invocare Codex; eventuali script di orchestrazione del workflow che invocano Codex CLI devono essere introdotti solo in uno step dedicato e richiesto esplicitamente.

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

Workflow agent-driven documentato. Pipeline locale implementata fino alla selezione del transcript di analisi: raw, review, normalizzazione conservativa e selector Step 5. Nessuna orchestrazione end-to-end o chiamata Codex da script e' implementata.
