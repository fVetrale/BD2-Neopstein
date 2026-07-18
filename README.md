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
Esegue in sequenza ETL, creazione di constraint/indici e import in Neo4j; si interrompe con exit code non zero al primo stadio che fallisce.

### Query su Cluster
`src/queries/cluster.py` espone tre query Python riutilizzabili per interrogare i `Cluster` del grafo: le mail appartenenti a un cluster, le persone coinvolte in un cluster e i cluster con più email redatte.

Con i servizi attivi e i dati importati, esegui:
```bash
python -m src.queries.cluster
```
Usa le stesse env var del resto del progetto (`.env`) per la connessione a Neo4j: se lo esegui dall'host verso il container Docker esposto, l'URI è `bolt://localhost:7687`; se lo esegui dentro un container della rete Docker, è `bolt://neo4j:7687`. Sono disponibili anche i flag opzionali `--cluster-id` (default: il primo cluster trovato nel DB) e `--limit` (default: 10).

Esempio di output:
```
$ python -m src.queries.cluster
--- Mail del cluster 52 ---
[{'id': 'EFTA01998334-0',
  'probability': 1.0,
  'redaction_count': 2,
  'sent_at': '2012-07-31T01:45:11+00:00',
  'subject': 'Barbro Ehnbom'},
 ... (altre mail del cluster omesse per brevità) ...]
--- Persone coinvolte nel cluster 52 ---
[{'display_name': 'jeffrey E.', 'is_epstein': True, 'is_unknown': False, 'person_id': 'jeffrey e'},
 {'display_name': 'Sarah', 'is_epstein': False, 'is_unknown': False, 'person_id': 'sarah'},
 {'display_name': 'Cecilia Steen', 'is_epstein': False, 'is_unknown': False, 'person_id': 'cecilia steen'}]
--- Top 10 cluster per redazioni totali ---
[{'cluster_id': 43, 'label': 'Epstein Case', 'total_redactions': 4635},
 {'cluster_id': 135, 'label': 'Private Matters', 'total_redactions': 4455},
 {'cluster_id': 222, 'label': 'Travel', 'total_redactions': 3625},
 {'cluster_id': 219, 'label': 'Social Calendar', 'total_redactions': 2501},
 {'cluster_id': 14, 'label': 'Reminders', 'total_redactions': 1610},
 {'cluster_id': 203, 'label': 'Epstein', 'total_redactions': 1324},
 {'cluster_id': 139, 'label': 'Personal Messages', 'total_redactions': 1303},
 {'cluster_id': 252, 'label': 'Apartment Cleaning', 'total_redactions': 1172},
 {'cluster_id': 265, 'label': 'Travel Arrangements', 'total_redactions': 884},
 {'cluster_id': 124, 'label': 'Pedophile', 'total_redactions': 770}]
```

## 📂 Struttura del Progetto
Di seguito l'alberatura delle directory principali del progetto:

```text
BD2-Neopstein/
├── data/
│   ├── raw/                  # Dataset originale (es. file .parquet) - NON COMMITTATO
│   ├── processed/            # File CSV puliti e pronti per l'import in Neo4j
│   └── ml_output/            # Eventuali output analitici
├── docs/                     # Diagrammi concettuali (ER, Graph Schema) e documentazione
├── notebooks/                # Notebook Jupyter per esplorazione dati e prototipazione
├── scripts/
│   └── run_import.sh         # Script Bash per automatizzare i processi di ETL e import
├── src/                      # Codice sorgente principale
│   ├── cli.py                # Entrypoint principale da riga di comando
│   ├── config.py             # Configurazione e variabili d'ambiente (dal file .env)
│   ├── db.py                 # Connettore e wrapper per le sessioni verso Neo4j
│   ├── schema.py             # Configurazione di constraint e indici del grafo
│   ├── etl/                  # Logiche di Extract, Transform, Load
│   │   ├── build_csv.py      # Script per la creazione dei nodi/relazioni
│   │   ├── clean_data.py     # Script di pulizia dati
│   │   └── import_data.py    # Script per caricamento su Neo4j
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
