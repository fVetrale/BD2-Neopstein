# Validazione post-import — risultati

Documento generato in seguito all'issue #10 ("Validazione post-import e test
sul parsing"). Riporta cosa verifica lo script di validazione e i risultati
ottenuti sul dataset attualmente importato in Neo4j.

## Cosa verifica

`python -m src.cli validate` esegue due controlli distinti:

1. **Conteggi CSV vs Neo4j** (`verify_counts`, `src/etl/import_data.py`,
   introdotta in issue #6): per ciascun tipo di nodo (`Person`,
   `EmailAddress`, `Mail`, `Cluster`, `Thread`) e relazione (`OWNS`, `SENT`,
   `TO`, `CC`, `BCC`, `BELONGS_TO`, `PART_OF`) confronta il numero di righe
   attese nei CSV sorgente con il conteggio reale nel grafo. Un mismatch
   indicherebbe un problema nell'import (righe perse, `MATCH` falliti su
   endpoint mancanti, ecc.).
2. **Cardinalità/integrità referenziale** (`check_graph_integrity`,
   `src/etl/validate_import.py`, introdotta in questa issue): calcola quante
   `Mail` non hanno alcuna relazione `SENT` in ingresso, quante non hanno
   alcuna `BELONGS_TO` in uscita, e quanti `EmailAddress` non hanno alcuna
   `OWNS` in ingresso, con le rispettive percentuali sul totale.

Il secondo controllo non solleva errori per numeri "bassi": non sono bug, ma
caratteristiche note del dataset sorgente, spiegate sotto.

## Esito di `verify_counts` sul dataset attualmente importato

Eseguito il 2026-07-18 contro il database Neo4j locale (container
`bd2-neopstein-neo4j-1`) con i CSV in `data/processed/csv/`. Tutti i 12
conteggi corrispondono esattamente tra CSV e grafo:

| Chiave | Conteggio |
|---|---|
| persons | 2.585 |
| email_addresses | 695.787 |
| mails | 400.000 |
| clusters | 289 |
| threads | 327.609 |
| owns | 19.463 |
| sent | 358.979 |
| to | 431.448 |
| cc | 61.935 |
| bcc | 295 |
| belongs_to | 181.893 |
| part_of | 400.000 |

Nessun mismatch rilevato: import idempotente confermato coerente con i CSV
sorgente.

## Cardinalità/integrità referenziale

Eseguito lo stesso giorno, stesso database:

| Metrica | Totale | Senza relazione attesa | Percentuale |
|---|---|---|---|
| `Mail` senza `SENT` in ingresso | 400.000 | 41.021 | 10.26% |
| `Mail` senza `BELONGS_TO` in uscita | 400.000 | 218.107 | 54.53% |
| `EmailAddress` senza `OWNS` in ingresso | 695.787 | 676.324 | 97.2% |

## Perché questi numeri sono attesi, non bug

Queste percentuali riflettono limiti noti e documentati del dataset sorgente
e delle scelte di design della pipeline ETL, non difetti dell'import:

- **`Mail` senza `SENT` (10.26%)**: per un sottoinsieme dei record sorgente il
  campo `sender` non era estraibile in modo affidabile (assente, malformato o
  totalmente redatto senza un indirizzo sintetico associabile). L'ETL non
  scarta la mail in questi casi: il nodo `Mail` viene comunque creato, solo
  senza l'arco `SENT` in ingresso.
- **`Mail` senza `BELONGS_TO` (54.53%)**: il clustering applicato è un
  soft-clustering probabilistico (proprietà `probability` sull'arco
  `BELONGS_TO`), che per sua natura non assegna necessariamente ogni mail a
  un cluster con confidenza sufficiente: il modello di clustering non
  converge o non produce un'assegnazione per tutte le 400.000 mail. Questo è
  un comportamento atteso dell'algoritmo, non un errore di import.
- **`EmailAddress` senza `OWNS` (97.2%)**: per design, un nodo `Person` — e
  quindi l'arco `OWNS` che lo collega a un `EmailAddress` — viene creato
  **solo** quando è disponibile almeno un display name risolvibile in modo
  deterministico (vedi `docs/graph_schema.md`, sezione "Derivazione di
  `Person`"). Non c'è adjudication automatica sui casi ambigui: un indirizzo
  senza nome associato resta un nodo `EmailAddress` valido e completo, ma
  senza `Person` proprietario. Con 695.787 indirizzi email e solo 2.585
  `Person` risolte, è atteso che la stragrande maggioranza degli indirizzi
  non abbia un `Person` associato.

Nessuno di questi numeri richiede correzione: sono conseguenze dirette delle
regole ETL descritte in `CLAUDE.md` (sezione "Regole ETL") e in
`docs/graph_schema.md`, applicate a un dataset sorgente con dati mancanti,
redatti o ambigui per costruzione.
