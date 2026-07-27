# Pipeline ETL

Documento di dettaglio sulla fase ETL: `.parquet` sorgente → CSV per entità → import in Neo4j. Per il modello a grafo vedi `graph_schema.md`; per le anomalie note del dataset post-import vedi `validation_findings.md`; per il diagramma di flusso vedi `diagram/etl_pipeline_flow.md`.

## Panoramica

```
data/raw/*.parquet
      │
      ▼  src/etl/clean_data.py + entity_resolution.py
src/etl/build_csv.py  ──────────────►  data/processed/csv/*.csv
      │
      ▼  src/schema.py (constraint/indici, PRIMA dell'import)
src/etl/import_data.py  ────────────►  Neo4j
      │
      ▼
src/etl/validate_import.py  (conteggi + integrità referenziale)
```

Orchestrata da `scripts/run_import.sh`:

```bash
python -m src.cli etl       # build_graph_csvs
python -m src.cli schema    # apply_schema_with_driver
python -m src.cli import    # run_import + verify_counts
```

`python -m src.cli validate` esegue `verify_counts` + `check_graph_integrity` senza reimportare.

## Fase 1 — Parsing indirizzi (`clean_data.py`)

Parsing **deterministico**, mai LLM: `json.loads` + regex.

- `parse_address_entry(raw)` — estrae `(nome, indirizzo)` da entry tipo `"Nome <indirizzo>"` o `"<indirizzo>"` con regex `^(.*?)\s*<([^>]+)>$`. Se non matcha, l'intera stringa trimmata è l'indirizzo e il nome è `None`.
- `normalize_address` — lowercase + trim.
- `extract_domain` — parte dopo `@`, `None` se assente.
- `is_redacted_address` — vero se l'indirizzo non contiene `@`.
- `parse_recipient_field(raw_json, mail_id, field)` — decodifica il campo JSON (`sender`/`to_recipients`/`cc_recipients`/`bcc_recipients`); se il JSON non è valido, fa fallback trattando l'intera stringa come singola entry. Per ogni entry:
  - se redacted → indirizzo sintetico `redacted:<mail_id>:<field>:<n>`, `is_redacted=True`, `domain=None`;
  - altrimenti → indirizzo normalizzato, `domain` estratto, `is_redacted=False`.

Il campo `sender` ha un pre-check dedicato in `build_csv.py::_parse_sender`: se il JSON decodifica a un tipo non-lista (int/float/stringa nuda), il parsing è considerato fallito e la relazione `SENT` viene **skippata per quella mail** (non l'intera riga) — contata in `sent_skipped_parse_failure`.

## Fase 2 — Entity resolution (`entity_resolution.py`)

Risolve i `Person` a partire dai display name grezzi raccolti su tutte le mention (sender/to/cc/bcc) di **tutto il dataset**, con union-find deterministico. Nessuna adjudication LLM: solo regole.

Pipeline pura, senza I/O — testabile standalone.

1. **Normalizzazione** (`normalize_name`): lowercase, trim, rimozione punteggiatura, collasso whitespace.
2. **Match cognome+iniziale** (`surname_initial_keys`): per un nome a ≥2 token genera entrambe le chiavi `(ultimo_token, iniziale_primo)` e `(primo_token, iniziale_ultimo)`, per coprire sia "Nome Cognome" che "Cognome Nome". Nomi con la stessa chiave vengono unificati (union).
3. **Indirizzo non-redacted condiviso**: due gruppi già formati che condividono almeno un `EmailAddress` non-redacted vengono unificati. Gli indirizzi `redacted:...` sono esclusi da questa regola (non sono identificativi).
4. **Gruppi finali**: quanto le regole 1-3 non riescono a fondere resta distinto — nessuna euristica probabilistica ulteriore, nessuna decisione automatica su casi ambigui.

Per ogni gruppo finale:
- `display_name` = variante raw più frequente (a parità, ordine alfabetico);
- `person_id` = `normalize_name(display_name)`;
- `is_unknown` = vero se il nome è degenerato (`_is_degenerate`: <2 caratteri o nessun carattere alfabetico);
- `is_epstein` = vero se un qualsiasi indirizzo del gruppo compare tra gli `epstein_sender_addresses` (flag `epstein_is_sender` del parquet, propagato per indirizzo mittente).

`ResolutionResult.raw_name_to_person_id` mappa ogni variante raw vista → `person_id`, usata poi da `build_csv.py` per costruire `OWNS`.

Nota: le mention con nome `None` (indirizzo senza nome associato) **non entrano** nella resolution — l'`EmailAddress` esiste comunque come nodo, ma non genera relazione `OWNS`.

## Fase 3 — Costruzione CSV (`build_csv.py`)

`build_graph_csvs(parquet_path, output_dir)`:

1. Legge il parquet **a batch** con `pyarrow.parquet.ParquetFile.iter_batches` (batch size 10 000, mai l'intero file in memoria, niente pandas).
2. Per ogni riga: parsa `sender`/`to`/`cc`/`bcc`, accumula indirizzi unici, mention `(nome, indirizzo)`, cluster (skip se `cluster == -1`, cioè "non clusterizzato"), thread (`doc_id`) e posizione nel thread (`message_index`).
3. Dopo aver processato **tutte** le righe, chiama una sola volta `entity_resolution.resolve_persons(mentions, epstein_sender_addresses)` sull'intero dataset.
4. Ricostruisce `OWNS` incrociando le mention originali con `raw_name_to_person_id`.
5. Scrive i CSV in `data/processed/csv/` (uno per nodo/relazione, vedi tabella sotto).
6. Stampa un report riepilogativo (righe processate, conteggi, SENT skippate, esito entity resolution).

### CSV prodotti

| File | Colonne | Corrisponde a |
|---|---|---|
| `persons.csv` | `person_id, display_name, is_unknown, is_epstein` | nodi `Person` |
| `email_addresses.csv` | `address, domain, is_redacted` | nodi `EmailAddress` |
| `mails.csv` | `id, subject, body, sent_at, redaction_count, redaction_ratio, attachment_count, is_promotional` | nodi `Mail` |
| `clusters.csv` | `cluster_id, label` | nodi `Cluster` (esclude `cluster_id = -1`) |
| `threads.csv` | `doc_id` | nodi `Thread` |
| `owns.csv` | `person_id, address` | `(Person)-[:OWNS]->(EmailAddress)` |
| `sent.csv` | `address, mail_id` | `(EmailAddress)-[:SENT]->(Mail)` |
| `to.csv` / `cc.csv` / `bcc.csv` | `mail_id, address` | `(Mail)-[:TO\|:CC\|:BCC]->(EmailAddress)` |
| `belongs_to.csv` | `mail_id, cluster_id, probability` | `(Mail)-[:BELONGS_TO {probability}]->(Cluster)` |
| `part_of.csv` | `mail_id, doc_id, position` | `(Mail)-[:PART_OF {position}]->(Thread)` |

## Fase 4 — Schema Neo4j (`schema.py`)

`apply_schema_with_driver` va eseguito **prima** dell'import. Idempotente (`IF NOT EXISTS`):

- Unique constraint su tutte le chiavi di nodo: `person_id`, `address`, `id` (Mail), `cluster_id`, `doc_id`.
- Indici non-unique su `Mail.sent_at` e `EmailAddress.domain` (colonne usate nei filtri delle query).

## Fase 5 — Import in Neo4j (`import_data.py`)

`run_import(driver, csv_dir, batch_size=5000)`:

- Legge ogni CSV **a streaming** (`csv.DictReader`, mai l'intero file in memoria), applica i converter di tipo necessari (bool/int/float — le colonne non convertite restano stringhe), e lo importa a batch tramite `UNWIND $rows AS row ...`.
- **Ordine**: prima tutti i nodi (`persons`, `email_addresses`, `mails`, `clusters`, `threads`), poi tutte le relazioni (`owns`, `sent`, `to`, `cc`, `bcc`, `belongs_to`, `part_of`) — gli endpoint devono esistere prima del `MATCH` nelle query di relazione.
- Ogni import usa **`MERGE`** sulla chiave del nodo/relazione (mai `CREATE` puro): l'intera pipeline è idempotente, rieseguibile senza duplicare dati.
- Le relazioni con proprietà (`belongs_to.probability`, `part_of.position`) fanno `MERGE` sull'arco e poi `SET` sulla proprietà.

### Verifica conteggi (`verify_counts`)

Confronta, per ciascuna entità/relazione, il conteggio atteso (righe CSV) con quello reale nel DB (query Cypher `count(...)`). Per le relazioni **senza proprietà proprie** (`owns`, `sent`, `to`, `cc`, `bcc`) il conteggio atteso è calcolato su **righe distinte**, perché `MERGE` collassa duplicati esatti del CSV in un solo arco — confrontare con le righe grezze produrrebbe falsi mismatch.

## Fase 6 — Validazione integrità (`validate_import.py`)

`check_graph_integrity(driver)` — complementare a `verify_counts`: non conta CSV vs DB, ma quante entità nel grafo **mancano** di relazioni attese:

- `Mail` senza `SENT` in ingresso (mail senza mittente risolto — es. parsing fallito, vedi Fase 1);
- `Mail` senza `BELONGS_TO` in uscita (mail non clusterizzata, `cluster == -1` nel sorgente);
- `EmailAddress` senza `OWNS` in ingresso (indirizzo mai associato a un nome).

Percentuali "basse" non indicano bug: sono caratteristiche note del dataset, documentate in `validation_findings.md`. `format_integrity_report` produce un report testuale leggibile da CLI (`python -m src.cli validate`).

## Punti di attenzione / edge case

- **`sender` non processabile**: JSON valido ma non-lista (int/float/stringa nuda) → relazione `SENT` skippata per quella mail, il nodo `Mail` viene comunque creato. Contato in `sent_skipped_parse_failure` nel report di `build_graph_csvs`.
- **Redacted recipients**: mai scartati — creano un `EmailAddress` sintetico `redacted:<mail_id>:<field>:<n>`, escluso dalla regola di merge per indirizzo condiviso in entity resolution (non è un identificativo reale).
- **Cluster `-1`**: convenzione del dataset sorgente per "non clusterizzato" — niente nodo `Cluster`, niente `BELONGS_TO` per quella mail.
- **Nomi mancanti**: se un'entry non ha nome (`name is None`), l'`EmailAddress` viene comunque creato ma non genera `OWNS` né entra nell'entity resolution.
- **Determinismo**: nessuno step della pipeline (parsing, entity resolution, import) chiama un LLM o introduce non-determinismo; a parità di parquet sorgente, i CSV e il grafo risultante sono riproducibili byte-per-byte (a meno dell'ordine di iterazione di insiemi Python, che non influisce sul contenuto).
