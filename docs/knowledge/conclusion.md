# Conclusioni di progetto — risultati e benchmark

Stato al merge della PR #32 (2026-07-19): 19/19 issue chiuse, 13 PR mergiate, 0 issue aperte.

## 1. Cosa è stato costruito

Pipeline completa in tre fasi, come da `CLAUDE.md`:

1. **ETL** (`src/etl/`): parsing deterministico degli indirizzi email (`clean_data.py`,
   issue #3/#21), entity resolution su display name (`entity_resolution.py`, issue #16),
   costruzione CSV nodi/relazioni con modellazione `Thread` (`build_csv.py`, issue #4/#17).
2. **Import in Neo4j** (`src/schema.py`, `src/etl/import_data.py`): constraint/indici
   idempotenti (issue #5) e import batch via `UNWIND` con `MERGE` (issue #6), più verifica
   di integrità post-import (`validate_import.py`, issue #10).
3. **API REST** (`src/api/`): FastAPI con 19 endpoint — 8 di analisi che espongono le query
   Cypher riutilizzabili di `src/queries/` (issue #7/#8/#9/#15) e 11 CRUD su Mail/Person/Cluster
   (issue #14), documentati via Swagger/ReDoc auto-generati e una collection Postman
   (`notebooks/postman_collection.json`).

Documentazione: `docs/report.md` (schema, motivazioni, confronto grafo vs relazionale, query
con output reali — issue #11), `docs/validation_findings.md` (issue #10), README end-to-end
riverificato dal vivo (issue #12).

## 2. Dimensione del codice

| Area | Righe (solo `.py`) |
|---|---|
| `src/etl/` | 970 |
| `src/api/` | 529 |
| `src/queries/` | 353 |
| `src/crud/` | 216 |
| `src/*.py` (root: `cli.py`, `schema.py`) | 176 |
| `tests/` | 2.077 |

110 test automatici (`pytest`), tutti su sessioni/driver Neo4j fake — nessuna dipendenza da
un database reale in CI. 19 endpoint HTTP totali.

## 3. Processo

| Metrica | Valore |
|---|---|
| Issue chiuse | 19 |
| PR mergiate | 13 |
| Commit su `main` | 44 |
| Durata (primo → ultimo commit) | 2026-05-05 → 2026-07-19 |

Workflow: PM → issue-manager → developer/reviewer per ogni issue, con checkpoint umano
obbligatorio prima di ogni push/PR/merge (mai eseguiti in autonomia dagli agenti).

## 4. Il grafo finale

Conteggi reali verificati (`python -m src.cli validate`, coincidenti al 100% con i CSV sorgente
su tutti i 12 tipi nodo/relazione):

| Nodo | Conteggio | | Relazione | Conteggio |
|---|---|---|---|---|
| `Person` | 2.585 | | `OWNS` | 19.463 |
| `EmailAddress` | 695.787 | | `SENT` | 358.979 |
| `Mail` | 400.000 | | `TO` | 431.448 |
| `Cluster` | 289 | | `CC` | 61.935 |
| `Thread` | 327.609 | | `BCC` | 295 |
| | | | `BELONGS_TO` | 181.893 |
| | | | `PART_OF` | 400.000 |

## 5. Benchmark

Misurati sull'ambiente locale (container Docker `neo4j:5`, stesso host di sviluppo — numeri
indicativi, non su hardware dedicato/isolato).

**Pipeline end-to-end** (`./scripts/run_import.sh`: ETL + schema + import su 400.000 mail):

| Esecuzione | Tempo |
|---|---|
| Import iniziale (issue #6, dataset da zero) | 74.15 s |
| Re-run idempotente (issue #12, verifica riproducibilità) | ~125 s |

La seconda esecuzione è più lenta della prima: ogni riga passa comunque per un `MERGE`
(verifica di esistenza + eventuale `SET`) anche quando il nodo/arco esiste già, quindi non
c'è un vero "fast path" per il caso idempotente — costo atteso, non un'anomalia.

**Comandi CLI** (query singole, connessione locale `bolt://localhost:7687`):

| Comando | Tempo |
|---|---|
| `python -m src.cli validate` (12 conteggi + 3 metriche di cardinalità su 400k/696k nodi) | 2.94 s |
| `python -m src.queries.cluster --cluster-id 52` (3 query) | 0.41 s |
| `python -m src.queries.person "daphne wallace"` (3 query, persona con 92 indirizzi) | 0.19 s |
| `python -m src.queries.mail <id>` (2 query) | 0.19 s |

**Endpoint API** (`curl -w time_total`, server locale già caldo):

| Endpoint | Tempo |
|---|---|
| `GET /clusters/52/mails?limit=20` | 16 ms |
| `GET /clusters/top-redacted?limit=10` (aggregazione su tutte le Mail) | 149 ms |
| `GET /persons/atci3/mails` | 4 ms |
| `GET /mails/{id}` | 6 ms |
| `GET /mails/{id}/persons` | 8 ms |

`top-redacted` è l'unico endpoint sensibilmente più lento perché aggrega `redaction_count` su
tutte le 400.000 `Mail` senza filtro; gli altri sono trascurabili perché filtrano per chiave
indicizzata (`cluster_id`, `person_id`, `mail.id`) prima di espandere il pattern.

**Suite di test** (110 test, fake session, nessun Neo4j reale): 1.0–1.3 s su 3 run consecutive.

## 6. Limiti noti (non bug)

Da `docs/validation_findings.md`, riportati qui perché rilevanti per interpretare i numeri
sopra: 10.26% delle `Mail` non ha un `SENT` risolto, 54.53% non ha un `BELONGS_TO` (il
clustering è probabilistico e non assegna tutte le mail), 97.2% degli `EmailAddress` non ha
una `Person` proprietaria (creata solo quando un display name è risolvibile deterministicamente).
Sono conseguenze dirette delle regole ETL di `CLAUDE.md`, non difetti dell'import.

## 7. Cosa resta aperto (checkpoint umano, non delegabile agli agenti)

- `docs/report.md` (issue #11): non ancora rivisto da un altro membro del gruppo.
- README (issue #12): la riproducibilità end-to-end è stata verificata dal vivo dagli agenti,
  ma non da "una persona diversa dall'autore" come richiesto letteralmente dal Done-when.
