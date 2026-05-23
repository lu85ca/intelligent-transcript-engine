# Meeting Recipe

Usa questa recipe quando la trascrizione rappresenta una riunione, una call operativa o una discussione di lavoro.

## Quando usarla

- Meeting interni o con clienti.
- Standup, retrospettive, pianificazioni, review o call operative.
- Discussioni con decisioni, responsabilita' o prossime azioni.

## Segnali da riconoscere

- Speaker multipli o turni di parola.
- Agenda, update, blocchi, decisioni o follow-up.
- Frasi come "decidiamo", "assegno", "entro", "prossimo passo".
- Riferimenti a owner, scadenze, rischi o dipendenze.

## Output Markdown

- Titolo
- Tipo contenuto e confidence
- Executive summary
- Partecipanti
- Decisioni
- Action items con owner e scadenze
- Rischi e blocchi
- Domande aperte
- Follow-up
- Limiti della fonte

## Campi JSON

- `title`
- `content_type`
- `summary`
- `participants`
- `decisions`
- `action_items`
- `risks`
- `open_questions`
- `followups`
- `source_limitations`

## Cosa non inventare

- Non inventare partecipanti, ruoli, owner o scadenze.
- Non trattare una proposta come decisione se non viene accettata esplicitamente.
- Non creare action item se manca un'azione concreta.
- Usa `non rilevato` quando owner, scadenza o responsabilita' non sono presenti.
