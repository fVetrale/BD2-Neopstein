# BD2-Neopstein

Vedi `@README.md` per una panoramica generale (quando sarà compilato).

## WHAT (Struttura e Stack)
- **Scopo**: Pipeline automatizzata per estrarre dati da un file `.parquet` con importazione all'interno di un database a grafo Neo4j.
- **Tech Stack**: Python, Neo4j (Cypher), Docker Compose 
- **Architettura Principale**:
  - `src/cli.py`: Entrypoint principale da riga di comando
  - `src/etl/`: Moduli per la pulizia dati (`clean_data.py`), generazione (`build_csv.py`) e importazione in Neo4j (`import_data.py`).
  - `src/queries/`: Query Cypher.
  - `docs/`: Documentazione visiva e teorica (es. `@docs/graph_schema.png`).
  - `data/`: Dati grezzi e processati (da NON committare mai su Git).

## WHY (Obiettivi)
Il progetto punta a creare un'astrazione a grafo coerente per analizzare reti di comunicazioni email e identificare dinamicamente argomenti (cluster). È vitale mantenere il codice scalabile e focalizzato sulla corretta validazione dei cluster.

## HOW (Workflow e Regole per l'Agente)
- **Ambiente**: I servizi (es. Neo4j) vengono gestiti tramite `docker-compose.yml`. Le credenziali si leggono da `.env`.
- **Esecuzione**: Utilizza `scripts/run_import.sh` per simulare l'intero ciclo di ETL o testa i singoli moduli tramite `src/cli.py`.
- **Test e Validazione**: Prima di completare una feature o un refactor, assicurati che i test in `tests/` passino. Se aggiungi query, aggiungi anche i relativi test.
- **Progressive Disclosure (Contesto Ottimizzato)**:
  - Se lavori sul database, consulta sempre `src/schema.py` per vincoli e indici.
  - Non caricare in memoria o stampare mai il contenuto della cartella `data/`.
  - Non formattare il codice in autonomia, affidati a tool deterministici se necessari.
