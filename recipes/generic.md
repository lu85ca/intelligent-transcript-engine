# Generic Analysis Recipe

Usa questa recipe quando la classificazione e' incerta, quando la confidence e' bassa o quando la trascrizione non corrisponde chiaramente a meeting, webinar o video YouTube.

## Quando usarla

- Transcript misti o frammentari.
- Contenuti senza segnali forti di formato.
- Classificazione ambigua con `secondary_type` rilevante.
- Trascrizioni troppo brevi per scegliere una recipe specialistica.

## Segnali da riconoscere

- Mancanza di struttura conversazionale chiara.
- Assenza di speaker, agenda, domande del pubblico o segnali da creator.
- Tema principale identificabile ma formato non chiaro.
- Presenza di informazioni utili non legate a un formato specifico.

## Output Markdown

- Titolo
- Tipo contenuto e confidence
- Sintesi
- Punti chiave
- Fatti
- Interpretazioni
- Decisioni
- Action item
- Domande aperte
- Rischi
- Follow-up
- Limiti della fonte

## Campi JSON

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

## Cosa non inventare

- Non inventare titolo, autori, speaker o contesto.
- Non trasformare interpretazioni in fatti.
- Non aggiungere decisioni, azioni, rischi o follow-up non presenti o non deducibili.
- Usa `non rilevato` per ogni dato assente.
