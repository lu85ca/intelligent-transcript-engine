# YouTube Video Recipe

Usa questa recipe quando la trascrizione rappresenta un video YouTube, un tutorial, una recensione o un contenuto creator-led.

## Quando usarla

- Video YouTube, tutorial, recensioni, commenti, analisi o contenuti creator-led.
- Contenuti con tesi centrale, opinioni, consigli pratici o call to action.
- Trascrizioni con tono narrativo o persuasivo.

## Segnali da riconoscere

- Apertura da creator, inviti a iscriversi o call to action.
- Opinioni personali, valutazioni, ranking o raccomandazioni.
- Tutorial passo-passo, esempi pratici o demo.
- Sponsorship, prodotti citati o bias dichiarati.

## Output Markdown

- Titolo
- Tipo contenuto e confidence
- Tesi centrale
- Punti principali
- Fatti
- Opinioni
- Possibili bias
- Consigli pratici
- Takeaway
- Limiti della fonte

## Campi JSON

- `title`
- `content_type`
- `central_thesis`
- `main_points`
- `facts`
- `opinions`
- `biases`
- `practical_advice`
- `takeaways`
- `source_limitations`

## Cosa non inventare

- Non inventare titolo, canale, sponsor o link.
- Non presentare opinioni del creator come fatti.
- Non dedurre bias senza segnali testuali.
- Non aggiungere consigli pratici non presenti nella trascrizione.
- Usa `non rilevato` per informazioni assenti o ambigue.
