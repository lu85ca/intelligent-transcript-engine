# Domain Profile: SIGE IMU Document Flow

Usa questo domain profile solo quando viene selezionato esplicitamente dal workflow o quando la trascrizione contiene segnali chiari relativi al dominio SIGE IMU / flusso documentale.

Questo profilo non autorizza a inventare informazioni assenti dalla trascrizione. I termini, le normalizzazioni e le relazioni qui sotto servono a interpretare meglio contenuti effettivamente emersi, non a completare buchi informativi.

## Termini di dominio

- `SIGE IMU`: sistema o ambito applicativo relativo al flusso IMU.
- `Libra`: sistema documentale, se il contesto lo indica.
- `STARDAS`: sistema o componente citato nel flusso documentale.
- `DoQui Acta`: sistema di gestione documentale / archiviazione documentale, se citato nel contesto.
- `protocollazione`: attività o fase di registrazione/protocollo di un documento.
- `archiviazione documentale`: attività o fase di conservazione/archiviazione del documento.
- `firma`: attività, stato o requisito legato alla firma di un documento.
- `SmistaDocumento`: operazione, servizio o integrazione da trattare come elemento tecnico solo se emerge dalla trascrizione.

## Normalizzazioni

Applica queste normalizzazioni solo se il contesto supporta chiaramente il riferimento:

- `Stardus`, `Stardust` o forme simili → `STARDAS`, salvo ambiguità.
- `libro` o `librora` → `Libra`, solo se dal contesto indica il sistema documentale.
- `CJ IMU` → `SIGE IMU`.

Se la normalizzazione è incerta, segnala il termine come `da confermare` o `punto aperto`.

## Regole di utilizzo

- Non introdurre SIGE IMU, Libra, STARDAS, DoQui Acta, protocollazione, archiviazione documentale, firma o SmistaDocumento se non emergono dalla trascrizione o se questo domain profile non è stato selezionato.
- Non dedurre integrazioni, stati, responsabilità o componenti tecnici non citati.
- Non trasformare ipotesi o proposte in decisioni confermate.
- Se un passaggio del flusso non è specificato, usare `non specificato nella trascrizione`, `da confermare` o `punto aperto`.
- Dichiarare sempre nella classification quando questo domain profile viene usato.
