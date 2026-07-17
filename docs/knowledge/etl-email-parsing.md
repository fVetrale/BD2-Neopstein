# Parsing indirizzi email: formato reale vs spec (issue #3, #21)

## Contesto

La spec originale dell'issue #3 assumeva che `sender`, `to_recipients`, `cc_recipients`,
`bcc_recipients` fossero sempre array JSON di stringhe (`["Nome <indirizzo>", ...]`).
Verificando su tutto il dataset reale (`data/raw/jmail_emails_clustered_sample_thread_aware.parquet`,
400.000 righe — solo conteggi aggregati, mai contenuto reale ispezionato/stampato), è emerso che
questo vale solo per una parte dei campi.

## Conformità reale al formato JSON array, per campo

| Campo             | JSON array valido | Stringa nuda (non-JSON) |
|--------------------|-------------------|--------------------------|
| `sender`           | 0.013% (52/400.000) | 99.987% |
| `to_recipients`     | 71.87%             | 28.13% |
| `cc_recipients`     | 100%               | 0% |
| `bcc_recipients`    | 100%               | 0% |

`sender` è quasi sempre una singola stringa `"Nome <indirizzo>"` o `"<indirizzo>"`, non incapsulata
in `[...]`. `to_recipients` è un caso misto. `cc`/`bcc` sono sempre conformi.

## Fix implementato (`src/etl/clean_data.py::parse_recipient_field`)

1. **`json.loads` fallisce (`JSONDecodeError`)** → l'intero valore del campo viene trattato come
   una singola entry bare, riusando `parse_address_entry` esistente invece di un parser diverso.
2. **Elemento `null` dentro un array JSON altrimenti valido** (trovata almeno un'occorrenza reale in
   `cc_recipients`) → normalizzato a stringa vuota prima del parsing; il pipeline esistente lo tratta
   già come redacted (nessun `@` → chiave sintetica), senza bisogno di un ramo dedicato.
3. **Chiavi sintetiche per entry fully-redacted** includono il nome del campo
   (`redacted:<mail_id>:<field>:<n>`), non solo l'indice. Un bug trovato in review: senza il nome
   campo, una entry redacted in `to_recipients[0]` e una in `cc_recipients[0]` della stessa mail
   generavano lo stesso indirizzo sintetico, collassando due nodi `EmailAddress` distinti in uno
   solo al `MERGE` in Neo4j.

## Residuo noto, documentato e accettato (non fixato)

**46 righe su 400.000** (tutte nel campo `sender`, 0 su to/cc/bcc): `json.loads` ha successo ma il
risultato non è una lista — è un `int` (45 casi) o un `float` (1 caso). Il loop fallisce con
`TypeError` perché un numero non è iterabile.

Diagnosi: probabile valore numerico (es. un ID o timestamp) finito per errore nel campo `sender`
a monte, nel dataset sorgente. Non è un problema di parsing ma di qualità del dato di origine.

**Decisione**: non gestito. Costo/beneficio non giustifica l'estensione per lo 0.0115% delle righe;
l'issue #21 accetta esplicitamente "eccezioni residue documentate e giustificate" come esito valido.
Se in futuro serve azzerarle, il fix è banale: se `json.loads` riesce ma il risultato non è una
lista, avvolgerlo come singola entry bare (`entries = [str(entries)]`), stessa logica già usata per
il fallback su `JSONDecodeError`.

## Implicazioni per issue future

- **#4** (costruzione dataframe): può consumare `parse_recipient_field` così com'è. Va previsto che,
  per le 46 righe residue, la chiamata sollevi `TypeError` sul campo `sender` — va gestita a livello
  di riga (skip + log conteggio) nella pipeline di build, non nel parser.
- **#16** (entity resolution Person): i nomi provenienti da entry bare (fallback #21) hanno la stessa
  forma di quelli da array JSON — nessun impatto sulla logica di risoluzione.

## Riferimenti

- Issue #3 — parsing base (assumeva sempre JSON array)
- Issue #21 — fallback per formato non-JSON, elemento `null`
- PR #22 — merge del parsing base + fix collisione chiavi redacted
