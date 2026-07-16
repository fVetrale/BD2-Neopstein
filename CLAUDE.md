# BD2-Neopstein

Vedi `@README.md` per una panoramica generale (quando sarà compilato).

## WHAT (Struttura e Stack)
- **Scopo**: Pipeline in tre fasi: ETL da file `.parquet` (email) → CSV per entità → importazione in Neo4j → API REST (FastAPI) che espone query e operazioni CRUD sul grafo.
- **Tech Stack**: Python, Neo4j (Cypher), FastAPI + Pydantic, Docker Compose. LLM locale (llama3.1, es. via Ollama) usato SOLO come fallback in fase ETL (vedi Regole ETL).
- **Architettura Principale**:
  - `src/cli.py`: Entrypoint principale da riga di comando
  - `src/etl/`: Pulizia dati (`clean_data.py`), generazione CSV (`build_csv.py`), importazione in Neo4j (`import_data.py`)
  - `src/crud/`: Operazioni CRUD per entità (`mail.py`, `person.py`, `cluster.py`). Parlano SOLO col driver Neo4j, nessuna dipendenza da HTTP. Sono usate da CLI, test e API.
  - `src/api/`: Layer FastAPI — `main.py` (app + lifecycle del driver), `deps.py` (dependency injection sessione Neo4j), `routers/` (un router per entità), `schemas/` (modelli Pydantic request/response)
  - `src/queries/`: Query Cypher pronte all'uso (file `.cypher` o costanti Python)
  - `src/schema.py`: Constraint e indici del grafo
  - `docs/`: Documentazione visiva e teorica (es. `@docs/graph_schema.png`)
  - `data/`: Dati grezzi e processati (da NON committare mai su Git)

## Modello a grafo (fonte di verità)
- **Nodi**:
  - `Person {person_id, display_name, is_unknown, is_epstein}`
  - `EmailAddress {address (chiave), domain, is_redacted}`
  - `Mail {id (chiave), subject, body, sent_at, redaction_count, redaction_ratio, attachment_count, is_promotional}`
  - `Cluster {cluster_id (chiave), label}`
  - `Thread {doc_id (chiave)}`
- **Relazioni**:
  - `(Person)-[:OWNS]->(EmailAddress)`
  - `(EmailAddress)-[:SENT]->(Mail)`
  - `(Mail)-[:TO|:CC|:BCC]->(EmailAddress)`
  - `(Mail)-[:BELONGS_TO {probability}]->(Cluster)`
  - `(Mail)-[:PART_OF {position}]->(Thread)` — position = `message_index`
- **Convenzioni**: label dei nodi in PascalCase, relazioni in MAIUSCOLO con underscore. Le proprietà delle relazioni (probability, position) NON vanno duplicate come proprietà dei nodi.
- Neo4j non impone cardinalità: sono documentate in `docs/` e verificate dai test post-import in `tests/`.

## Regole ETL
- I campi `sender`, `to_recipients`, `cc_recipients`, `bcc_recipients` sono array JSON di stringhe nel formato `"Nome <indirizzo>"` o `"<indirizzo>"`. Il parsing è DETERMINISTICO: `json.loads` + regex. Mai usare l'LLM per estrarre indirizzi.
- Voci di destinatario completamente REDACTED: creare un nodo `EmailAddress` sintetico (es. `redacted:<mail_id>:<n>`) con `is_redacted = true`. Non scartare mai la relazione.
- Il campo cluster contiene sia l'id numerico sia il nome: separarli in ETL in `cluster_id` (int) e `label` (string).
- Il nodo `Person` nasce da entity resolution sui display name (es. "Jeffrey Epstein" ≡ "J. Epstein" ≡ "Epstein Jeffrey"). Prima regole deterministiche (normalizzazione, confronto cognome+iniziale, indirizzi condivisi); l'LLM locale è SOLO il fallback per i casi ambigui. Ogni output LLM va cachato su file (`data/ml_output/`) così i run sono ripetibili e l'LLM non viene reinterrogato.
- Se un display name non è ricavabile, l'`EmailAddress` esiste comunque; `Person` si crea solo con un nome, altrimenti flag `is_unknown`.
- L'import è idempotente: sempre `MERGE` sulle chiavi, mai `CREATE` puro sui nodi. Constraint e indici (`src/schema.py`) vanno applicati PRIMA di ogni import.

## WHY (Obiettivi)
Il progetto punta a creare un'astrazione a grafo coerente per analizzare reti di comunicazioni email e identificare dinamicamente argomenti (cluster). È vitale mantenere il codice scalabile e focalizzato sulla corretta validazione dei cluster e delle relazioni tra persone.

## HOW (Workflow e Regole per l'Agente)
- **Ambiente**: I servizi (`neo4j`, `api`) vengono gestiti tramite `docker-compose.yml`. Le credenziali si leggono da `.env` (template committato in `.env.example`, mai committare `.env`).
- **Esecuzione**: Utilizza `scripts/run_import.sh` per l'intero ciclo ETL + import, oppure testa i singoli moduli tramite `src/cli.py`. L'API si avvia con uvicorn (`src.api.main:app`).
- **Regole API**: i router restano sottili — validazione Pydantic e chiamata a `src/crud/` o `src/queries/`. Nessuna query Cypher scritta inline nei router. Errori Neo4j mappati su HTTP status sensati (404, 409, 422).
- **Test e Validazione**: Prima di completare una feature o un refactor, assicurati che i test in `tests/` passino. Se aggiungi query o endpoint, aggiungi anche i relativi test (per l'API: `httpx`/`TestClient`). I test post-import verificano conteggi attesi e cardinalità.
- **Progressive Disclosure (Contesto Ottimizzato)**:
  - Se lavori sul database, consulta sempre `src/schema.py` per vincoli e indici e la sezione "Modello a grafo" di questo file.
  - Non caricare in memoria o stampare mai il contenuto della cartella `data/`.
  - Non formattare il codice in autonomia, affidati a tool deterministici se necessari.
