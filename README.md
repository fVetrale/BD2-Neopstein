# BD2-Neopstein (Epstein Files Graph Mapping)

## 📌 Contesto del Progetto
Il progetto **BD2-Neopstein** ha come obiettivo la creazione di una rappresentazione a grafo delle email del caso **Epstein** al fine di renderle interattive e facilmente navigabili. 
Partendo da un dataset già a nostra disposizione (in formato `.parquet`), il nostro compito è concentrato sull'estrazione dei dati, la loro eventuale trasformazione e la **mappatura definitiva all'interno di un database a grafo tramite Neo4j**.

L'utilizzo di un database a grafo ci permette di:
- Analizzare dinamicamente le reti di comunicazione e le connessioni tra le diverse identità (mittenti, destinatari, nodi cc/bcc).
- Rendere interrogabili volumi complessi di dati tramite query Cypher.
- Esplorare in modo visivo e analitico chi ha comunicato con chi.

## 🛠️ Stack Tecnologico
- **Linguaggio**: Python (per estrazione dal `.parquet` e logica di caricamento).
- **Database**: Neo4j (con linguaggio Cypher per le interrogazioni).
- **API**: FastAPI + Pydantic (query e CRUD sul grafo via REST).
- **Ambiente**: Docker Compose (per istanziare e gestire rapidamente Neo4j e l'API).

## 🚀 Setup del Progetto

### Prerequisiti
- Docker e Docker Compose

### 1. Configurazione ambiente
```bash
cp .env.example .env
```
Modifica `NEO4J_PASSWORD`/`NEO4J_AUTH` in `.env` se vuoi una password diversa da quella di default. Lascia `NEO4J_URI=bolt://neo4j:7687`: è il nome del servizio Docker, non `localhost`, perché l'API gira in un container separato da Neo4j.

### 2. Avvio dei servizi
```bash
docker compose up -d --build
```
Avvia due container:
- `neo4j`: Neo4j Browser su `http://localhost:7474`, Bolt su `bolt://localhost:7687`
- `api`: FastAPI su `http://localhost:8000`

### 3. Verifica che tutto funzioni
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```
In alternativa, apri `http://localhost:7474` nel browser ed effettua il login con `NEO4J_USER`/`NEO4J_PASSWORD`.

### 4. Pipeline ETL + import
Con i servizi attivi ed il dataset `.parquet` in `data/raw/`:
```bash
./scripts/run_import.sh
```
Esegue in sequenza ETL, creazione di constraint/indici e import in Neo4j; si interrompe con exit code non zero al primo stadio che fallisce. L'import è idempotente (`MERGE` sulle chiavi): eseguirlo più volte non duplica né corrompe i dati.

Al termine, come passo opzionale di verifica, puoi confermare conteggi e integrità del grafo importato:
```bash
python -m src.cli validate
```
Confronta i conteggi Neo4j con i CSV sorgente e stampa un report testuale sulla cardinalità delle relazioni (es. percentuale di `Mail` senza `SENT` in ingresso o senza `BELONGS_TO` in uscita).

## Query disponibili

Ogni modulo in `src/queries/` espone funzioni Python parametriche su `neo4j.Session` (stesso pattern di `src/schema.py`), eseguibili anche da riga di comando. Con i servizi attivi, usa le env var Neo4j: `bolt://localhost:7687` dall'host, `bolt://neo4j:7687` da un container sulla rete Docker.

| Modulo | Query esposte | Comando |
|---|---|---|
| `src/queries/cluster.py` | `get_cluster_mails`, `get_cluster_persons`, `get_top_redacted_clusters` | `python -m src.queries.cluster [--cluster-id ID] [--limit N]` |
| `src/queries/person.py` | `get_person_mails`, `get_person_addresses`, `get_connected_persons` | `python -m src.queries.person <person_id>` |
| `src/queries/mail.py` | `get_mail_info`, `get_mail_persons` | `python -m src.queries.mail <mail_id>` |

Esempio:
```bash
NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=changeme python -m src.queries.cluster --cluster-id 52
```

## Endpoint API

Ogni endpoint elenco (lista) accetta i query param `limit` (default `50`, tra `1` e `500`) e `offset` (default `0`) per la paginazione. `GET /mails/{mail_id}` ritorna un oggetto singolo e non è paginato.

| Metodo | Path | Query di riferimento | Descrizione |
|---|---|---|---|
| GET | `/clusters/{cluster_id}/mails` | `get_cluster_mails` | Mail appartenenti al cluster, con `probability` della relazione `BELONGS_TO` |
| GET | `/clusters/{cluster_id}/persons` | `get_cluster_persons` | Persone coinvolte (mittenti/destinatari) nelle mail del cluster |
| GET | `/clusters/top-redacted` | `get_top_redacted_clusters` | Classifica dei cluster per redazioni totali, ordinata decrescente |
| GET | `/persons/{person_id}/mails` | `get_person_mails` | Mail inviate o ricevute dalla persona |
| GET | `/persons/{person_id}/connected` | `get_connected_persons` | Persone connesse via scambio di email |
| GET | `/persons/{person_id}/addresses` | `get_person_addresses` | Indirizzi email posseduti dalla persona |
| GET | `/mails/{mail_id}` | `get_mail_info` | Dettaglio di una mail (404 se non esiste) |
| GET | `/mails/{mail_id}/persons` | `get_mail_persons` | Persone collegate alla mail con relativo ruolo (sender/to/cc/bcc) |
| POST | `/clusters` | `create_cluster` | Crea un nuovo cluster (409 se `cluster_id` esiste già) |
| GET | `/clusters/{cluster_id}` | `get_cluster` | Dettaglio di un cluster (404 se non esiste) |
| PUT | `/clusters/{cluster_id}` | `update_cluster` | Aggiorna la `label` di un cluster (404 se non esiste) |
| DELETE | `/clusters/{cluster_id}` | `delete_cluster` | Elimina un cluster (404 se non esiste) |
| POST | `/persons` | `create_person` | Crea una nuova persona (409 se `person_id` esiste già) |
| GET | `/persons/{person_id}` | `get_person` | Dettaglio di una persona (404 se non esiste) |
| PUT | `/persons/{person_id}` | `update_person` | Aggiorna le proprietà di una persona (404 se non esiste) |
| DELETE | `/persons/{person_id}` | `delete_person` | Elimina una persona (404 se non esiste) |
| POST | `/mails` | `create_mail` | Crea una nuova mail (409 se `id` esiste già) |
| PUT | `/mails/{mail_id}` | `update_mail` | Aggiorna le proprietà di una mail (404 se non esiste) |
| DELETE | `/mails/{mail_id}` | `delete_mail` | Elimina una mail (404 se non esiste) |

Esempi (con i servizi Docker attivi):
```bash
curl "http://localhost:8000/clusters/52/mails?limit=2"
curl "http://localhost:8000/clusters/52/persons"
curl "http://localhost:8000/clusters/top-redacted?limit=3"
curl "http://localhost:8000/persons/atci3/mails"
curl "http://localhost:8000/persons/atci3/connected"
curl "http://localhost:8000/persons/atci3/addresses"
curl "http://localhost:8000/mails/001612df62eb14194162f0a366793927"
curl "http://localhost:8000/mails/001612df62eb14194162f0a366793927/persons"
```

## Documentazione interattiva e collection Postman

| Risorsa | Percorso | Note |
|---|---|---|
| Swagger UI | `http://localhost:8000/docs` | Disponibile con i servizi Docker attivi |
| ReDoc | `http://localhost:8000/redoc` | Disponibile con i servizi Docker attivi |
| Postman Collection | `notebooks/postman_collection.json` | Import → File → seleziona il file; imposta la variabile di collection `base_url` se il servizio non gira su `http://localhost:8000` |

## Documentazione

| Documento | Percorso | Contenuto |
|---|---|---|
| Report finale | `docs/report.md` | Descrizione end-to-end del progetto: pipeline, modello a grafo, query, API |
| Findings di validazione | `docs/validation_findings.md` | Esiti della validazione dei dati importati (conteggi, cardinalità, anomalie) |

## 📂 Struttura del Progetto
Di seguito l'alberatura delle directory principali del progetto:

```text
BD2-Neopstein/
├── data/
│   ├── raw/                  # Dataset originale (es. file .parquet) - NON COMMITTATO
│   └── processed/            # File CSV puliti e pronti per l'import in Neo4j
├── docs/                     # Diagrammi concettuali (ER, Graph Schema), report e documentazione
├── notebooks/                # Notebook Jupyter e collection Postman
├── scripts/
│   ├── run_import.sh               # Script Bash per automatizzare i processi di ETL e import
│   └── validate_address_parsing.py # Script di supporto per validare il parsing degli indirizzi
├── src/                       # Codice sorgente principale
│   ├── cli.py                    # Entrypoint principale da riga di comando
│   ├── schema.py                 # Configurazione di constraint e indici del grafo
│   ├── etl/                      # Logiche di Extract, Transform, Load
│   │   ├── build_csv.py          # Script per la creazione dei nodi/relazioni
│   │   ├── clean_data.py         # Script di pulizia dati
│   │   ├── entity_resolution.py  # Entity resolution deterministica sui display name
│   │   ├── import_data.py        # Script per caricamento su Neo4j
│   │   └── validate_import.py    # Verifica conteggi e integrità post-import
│   ├── crud/                 # Operazioni CRUD sul grafo (usate da CLI, test e API)
│   ├── api/                  # Layer FastAPI (main.py, deps.py, routers/, schemas/)
│   └── queries/              # Raccolta delle query Cypher pronte all'uso
├── tests/                    # Moduli di test per importazione e query
├── docker-compose.yml        # Configurazione dei container Neo4j e API
├── Dockerfile                # Immagine del servizio API
├── .env.example              # Template delle variabili d'ambiente
├── requirements.txt          # Dipendenze Python
└── CLAUDE.md                 # Contesto e linee guida per LLM e Agent
```
