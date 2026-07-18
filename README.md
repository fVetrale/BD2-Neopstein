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

### Query su Mail
`src/queries/mail.py` espone due funzioni che, data una `neo4j.Session` e un `mail_id`, restituiscono strutture dati Python pronte all'uso (nessuna dipendenza da HTTP):
- `get_mail_info(session, mail_id)`: proprietà della `Mail` (subject, sent_at, redaction, ecc.) più le info del `Cluster` collegato (`cluster_id`, `label`, `probability`), oppure `None` se la mail non esiste.
- `get_mail_persons(session, mail_id)`: elenco delle `Person` collegate alla mail (mittente e destinatari), ciascuna con i ruoli in cui compare (`sender`, `to`, `cc`, `bcc`).

Il modulo è eseguibile anche da riga di comando:
```bash
python -m src.queries.mail mail-000123
```

Esempio schematico di output:
```text
Info mail:
{'id': 'mail-000123', 'subject': 'Re: incontro', 'sent_at': '2015-03-02T10:15:00', 'redaction_count': 0, 'redaction_ratio': 0.0, 'attachment_count': 1, 'is_promotional': False, 'cluster_id': 4, 'label': 'logistica-viaggi', 'probability': 0.87}
Persone collegate:
[{'person_id': 'p-001', 'display_name': 'Jeffrey Epstein', 'is_unknown': False, 'is_epstein': True, 'roles': ['sender']}, {'person_id': 'p-002', 'display_name': 'Ghislaine Maxwell', 'is_unknown': False, 'is_epstein': False, 'roles': ['cc', 'to']}]
```
Se la mail non è collegata a nessun `Cluster`, `cluster_id`, `label` e `probability` valgono `None`, ad esempio:
```text
{'id': 'mail-000123', 'subject': 'Promo newsletter', 'sent_at': '2015-01-10T08:00:00', 'redaction_count': 0, 'redaction_ratio': 0.0, 'attachment_count': 0, 'is_promotional': True, 'cluster_id': None, 'label': None, 'probability': None}
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
