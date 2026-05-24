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

## Flusso agent-driven

1. Inserire una trascrizione in `input/transcripts/`.
2. Codex legge `AGENTS.md`.
3. Codex usa `.agents/skills/transcript-intelligence/SKILL.md`.
4. Codex classifica la trascrizione.
5. Codex sceglie la recipe piu' adatta da `recipes/`.
6. Codex seleziona i knowledge context tramite `knowledge/registry.yml`.
7. Codex usa i template in `prompt_templates/` per generare un prompt ottimizzato.
8. Codex salva il prompt in `output/prompts/<nome>_generated_prompt.md`.
9. Codex applica il prompt alla trascrizione.
10. Codex salva:
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

Workflow agent-driven documentato. Struttura `knowledge/` iniziale presente. Non ci sono ancora script di pipeline, dipendenze esterne o chiamate API implementate.
