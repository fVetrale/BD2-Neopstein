# Report finale — Modellazione a grafo e risultati

Documento di sintesi del progetto BD2-Neopstein: dataset sorgente di email
(campione clusterizzato del corpus Epstein, formato `.parquet`), pipeline ETL
in tre fasi (pulizia dati → CSV per entità → import in Neo4j) e layer API
REST (FastAPI) che espone query e CRUD sul grafo risultante.

Questo report riassume le decisioni di modellazione, mostra un confronto
concreto grafo/relazionale, riporta output reali delle query implementate e
riepiloga la qualità del dato post-import. I documenti di design dettagliati
restano linkati come riferimento, non duplicati qui.

## 1. Schema ER → grafo e motivazioni

### 1.1 Modello ER relazionale del dataset sorgente

Il dataset `.parquet` non contiene tabelle relazionali esplicite: solo record
di mail con campi `sender`, `to_recipients`, `cc_recipients`,
`bcc_recipients` (stringhe `"Nome <indirizzo>"` o `"<indirizzo>"`, non sempre
incapsulate in array JSON — vedi §1.4), più campi di cluster e thread.

Prima di mappare a grafo, il progetto ha formalizzato come si modellerebbe
questo dataset in forma relazionale "pulita": entità `EMAIL_ADDRESS`,
`MAIL`, `CLUSTER`, `THREAD`, con tabelle associative `MAIL_RECIPIENT`
(ruolo TO/CC/BCC come colonna discriminante), `MAIL_CLUSTER` (con
`probability`) e `MAIL_THREAD` (con `position`). Non esiste un'entità
`PERSON` nel modello sorgente: solo indirizzi email e display name testuali
liberi. Schema ER completo in `docs/diagram/er_source_model.md`.

### 1.2 Modello a grafo Neo4j

La traduzione a grafo introduce cinque label di nodo e sette tipi di
relazione:

| Label | Chiave | Altre proprietà |
|---|---|---|
| `Person` | `person_id` | `display_name`, `is_unknown`, `is_epstein` |
| `EmailAddress` | `address` | `domain`, `is_redacted` |
| `Mail` | `id` | `subject`, `body`, `sent_at`, `redaction_count`, `redaction_ratio`, `attachment_count`, `is_promotional` |
| `Cluster` | `cluster_id` | `label` |
| `Thread` | `doc_id` | — |

| Relazione | Proprietà | Note |
|---|---|---|
| `(Person)-[:OWNS]->(EmailAddress)` | — | una persona può possedere più indirizzi |
| `(EmailAddress)-[:SENT]->(Mail)` | — | mittente della mail |
| `(Mail)-[:TO\|:CC\|:BCC]->(EmailAddress)` | — | un tipo di relazione per ruolo destinatario |
| `(Mail)-[:BELONGS_TO]->(Cluster)` | `probability` | soft-clustering, potenzialmente N:N |
| `(Mail)-[:PART_OF]->(Thread)` | `position` | `position = message_index` |

Diagramma completo in `docs/diagram/graph_model.md`, tabelle e dettagli in
`docs/graph_schema.md`.

### 1.3 Motivazioni della traduzione ER → grafo

Le differenze principali rispetto al modello relazionale (dettagliate in
`docs/graph_schema.md`, sezione "Differenze principali rispetto al modello
ER relazionale") si possono riassumere in quattro punti:

- **Proprietà sugli archi anziché tabelle ponte.** `probability` (cluster) e
  `position` (thread) diventano proprietà native della relazione
  (`BELONGS_TO.probability`, `PART_OF.position`), eliminando le tabelle
  associative `MAIL_CLUSTER`/`MAIL_THREAD` e i JOIN necessari a leggerle.
  Un esempio concreto con dati reali è nella sezione 2.
- **Ruolo del destinatario come tipo di relazione.** `TO`/`CC`/`BCC`
  sostituiscono una colonna discriminante (`recipient_type`) in
  `MAIL_RECIPIENT`: il ruolo è nello schema del grafo, interrogabile
  direttamente senza filtro.
- **Nessuna FK esplicita.** L'attraversamento `Person → EmailAddress → Mail`
  sostituisce i JOIN relazionali con pattern match, in entrambe le
  direzioni, senza indici dedicati su colonne FK.
- **Cardinalità non imposte dal DB.** A differenza di FK + UNIQUE
  relazionali, Neo4j non vincola nativamente le cardinalità; sono
  documentate qui e verificate a posteriori dai test di validazione
  post-import (si veda la sezione 4).

### 1.4 Entità senza mapping esplicito nel dataset sorgente

**`Person`** non esiste come entità nel dataset grezzo: nasce da entity
resolution deterministica sui display name testuali (normalizzazione,
confronto cognome+iniziale, indirizzi condivisi tra varianti di nome), con
fallback a un LLM locale solo per i casi ambigui residui non risolti dalle
regole (output cachato per rendere i run ripetibili). Un `EmailAddress`
senza nome ricavabile resta comunque un nodo valido, senza `Person`
proprietaria associata (`Person.is_unknown = true` quando il nodo esiste ma
senza nome). Pipeline dettagliata in `docs/diagram/person_resolution_flow.md`
e sezione "Derivazione di `Person`" di `docs/graph_schema.md`.

**`Thread`** è introdotto per ricostruire l'ordine delle conversazioni,
assente come entità nel dataset originale: la posizione del messaggio
(`message_index`) diventa la proprietà `position` di `PART_OF`, non un
attributo di `Mail`, perché significativa solo nel contesto di un thread
specifico.

**Parsing degli indirizzi email** (campi `sender`/`to_recipients`/
`cc_recipients`/`bcc_recipients`): la spec iniziale assumeva sempre array
JSON di stringhe, ma la verifica sul dataset reale (400.000 righe, solo
conteggi aggregati) ha mostrato che `sender` è JSON valido solo nello
0,013% dei casi (quasi sempre stringa nuda), `to_recipients` è misto
(71,87% JSON valido), mentre `cc`/`bcc` sono sempre conformi. Il parser
gestisce il fallback su stringa nuda quando `json.loads` fallisce, e
genera chiavi sintetiche per entry completamente redatte
(`redacted:<mail_id>:<field>:<n>`, con il nome del campo per evitare
collisioni tra `to`/`cc` sullo stesso indice). Un residuo di 46 righe su
400.000 (0,0115%, solo nel campo `sender`) resta non gestito per costo/
beneficio: `json.loads` riesce ma produce un valore non iterabile (int o
float), diagnosticato come difetto del dato sorgente, non del parser.
Dettaglio completo in `docs/knowledge/etl-email-parsing.md`.

## 2. Confronto concreto grafo vs relazionale: cluster 52

Oltre al confronto generale (§1.3), un esempio con dati reali dal database
importato: il cluster con `cluster_id = 52` (label `"BBB"`).

### 2.1 Query Cypher nel grafo

```cypher
MATCH (m:Mail)-[r:BELONGS_TO]->(c:Cluster {cluster_id: 52})
RETURN m.id AS id, m.subject AS subject, r.probability AS probability
```

Output reale (troncato alle prime righe, eseguito con
`python -m src.queries.cluster --cluster-id 52`):

```
{'id': 'EFTA01998334-0', 'subject': 'Barbro Ehnbom', 'probability': 1.0, 'redaction_count': 2, 'sent_at': '2012-07-31T01:45:11+00:00'}
{'id': 'vol00009-efta01165804-pdf', 'subject': 'Our new FEOY 2011 i Love & Kisses from Sth!!', 'probability': 0.9080871343612671, 'redaction_count': 0, 'sent_at': '2011-06-14T22:19:56+00:00'}
{'id': 'vol00009-efta01136076-pdf', 'subject': 'SALSS 2013 Save the Date', 'probability': 0.8999784588813782, 'redaction_count': 0, 'sent_at': '2013-05-09T15:40:02+00:00'}
{'id': 'vol00009-efta01051604-pdf', 'subject': 'Re: BBB', 'probability': 0.8947866559028625, 'redaction_count': 0, 'sent_at': '2017-03-21T18:29:35+00:00'}
```

Il cluster 52 contiene **237 mail** collegate via `BELONGS_TO`, ciascuna con
la propria `probability` (il soft-clustering assegna valori diversi da
1.0 a mail diverse). La `probability` è letta direttamente dalla
relazione attraversata: nessuna tabella intermedia, nessun JOIN.

### 2.2 Stessa cosa in un modello relazionale

Lo stesso dato, in un modello relazionale, richiederebbe una tabella ponte
esplicita `Mail_Cluster`:

```sql
CREATE TABLE Mail_Cluster (
    mail_id     VARCHAR REFERENCES Mail(id),
    cluster_id  INT     REFERENCES Cluster(cluster_id),
    probability FLOAT,
    PRIMARY KEY (mail_id, cluster_id)
);
```

E la query equivalente diventerebbe un JOIN a tre tabelle:

```sql
SELECT m.id, m.subject, mc.probability
FROM Mail m
JOIN Mail_Cluster mc ON mc.mail_id = m.id
JOIN Cluster c ON c.cluster_id = mc.cluster_id
WHERE c.cluster_id = 52;
```

**Differenza pratica.** Nel modello relazionale `probability` vive in una
riga a sé nella tabella ponte, raggiungibile solo tramite due JOIN (`Mail` →
`Mail_Cluster` → `Cluster`) e un indice su `Mail_Cluster.cluster_id` per
restare efficiente su 400.000 mail. Nel grafo, `probability` è una
proprietà nativa dell'arco `BELONGS_TO`: il pattern
`(m:Mail)-[r:BELONGS_TO]->(c:Cluster)` la espone direttamente in `r`, senza
join né tabella intermedia da mantenere/indicizzare a parte.

**Nota sulla cardinalità osservata.** Il modello del grafo (come quello
relazionale con `Mail_Cluster`) supporta nativamente N:N tra `Mail` e
`Cluster` (una mail potrebbe appartenere a più cluster con probabilità
diverse). Nei dati attualmente importati, verificato con
`MATCH (m:Mail)-[r:BELONGS_TO]->() WITH m, count(r) AS n WHERE n > 1 RETURN m`,
nessuna mail risulta collegata a più di un cluster: il modello di
clustering a monte assegna al più un cluster per mail. Questo non cambia la
validità del confronto (la struttura del modello resta N:N, `probability`
resta una proprietà d'arco), è solo una caratteristica osservata dei dati
attuali.

## 3. Query con output reali

Tutte le query sono state rieseguite dal vivo contro il container Neo4j
locale (`bd2-neopstein-neo4j-1`, dati reali) e, dove indicato, contro l'API
in esecuzione su `http://localhost:8000`. Nessun contenuto grezzo di
`data/` viene riportato: solo output aggregati o di singole entità, come
prodotto dalle query esistenti in `src/queries/`.

### 3.1 `get_cluster_mails` / `get_cluster_persons` — cluster 52

Comando: `python -m src.queries.cluster --cluster-id 52`.

`get_cluster_persons` — persone coinvolte nel cluster 52 (risalita
`Mail → EmailAddress → Person` su mittente e destinatari di tutte le 237
mail del cluster):

```
[{'display_name': 'jeffrey E.', 'is_epstein': True, 'is_unknown': False, 'person_id': 'jeffrey e'},
 {'display_name': 'Sarah', 'is_epstein': False, 'is_unknown': False, 'person_id': 'sarah'},
 {'display_name': 'Cecilia Steen', 'is_epstein': False, 'is_unknown': False, 'person_id': 'cecilia steen'}]
```

Corrisponde a quanto atteso: `jeffrey e`, `Sarah`, `Cecilia Steen`.

### 3.2 `get_top_redacted_clusters` — classifica cluster per redazioni

```
[{'cluster_id': 43, 'label': 'Epstein Case', 'total_redactions': 4635},
 {'cluster_id': 135, 'label': 'Private Matters', 'total_redactions': 4455},
 {'cluster_id': 222, 'label': 'Travel', 'total_redactions': 3625},
 {'cluster_id': 219, 'label': 'Social Calendar', 'total_redactions': 2501},
 {'cluster_id': 14, 'label': 'Reminders', 'total_redactions': 1610}]
```

Cluster 43 ("Epstein Case") è il più redatto: coerente con l'aspettativa
che i contenuti più sensibili legati direttamente al caso siano quelli con
più oscuramenti.

### 3.3 Query su una persona: `daphne wallace`

`daphne wallace` esiste ancora nel dataset con `person_id = "daphne wallace"`
(`display_name = "Daphne Wallace"`). Comando:
`python -m src.queries.person "daphne wallace"`.

Conteggio indirizzi posseduti, verificato con
`MATCH (p:Person)-[:OWNS]->(e:EmailAddress) RETURN p.person_id, count(e) ORDER BY count(e) DESC`:
`daphne wallace` possiede **92 `EmailAddress` distinti** e compare in
**154 `Mail`** (invio o ricezione). Estratto reale degli indirizzi (`GET
EmailAddress per person_id='daphne wallace'`, 92 totali):

```json
[
  {"address": "daphne.wallace@farragutacademy.org", "domain": "farragutacademy.org", "is_redacted": false},
  {"address": "daphne.wallace@gmail.com", "domain": "gmail.com", "is_redacted": false},
  {"address": "daphne.wallace@hbs.edu", "domain": "hbs.edu", "is_redacted": false},
  {"address": "daphne.wallace@latimes.com", "domain": "latimes.com", "is_redacted": false}
]
```

Questo caso è la prova pratica del perché l'entity resolution deterministica
descritta al §1.4 sia necessaria: la stessa persona compare nel dataset
sorgente con decine di indirizzi email diversi (domini istituzionali,
personali, professionali) legati a varianti/istanze diverse del suo display
name; senza risoluzione a un unico `Person`, ogni indirizzo resterebbe un
nodo isolato e l'analisi della rete di comunicazioni la conterebbe come
decine di entità distinte invece di una sola.

Nota: interrogando l'intero grafo per numero di indirizzi posseduti, la
persona con più indirizzi in assoluto è `jeffrey e` (Jeffrey Epstein, 12.218
`EmailAddress`), un caso estremo legato al volume di corrispondenza
dell'entità centrale del dataset; `daphne wallace`, con 92 indirizzi, resta
un esempio più rappresentativo del fenomeno su un soggetto "qualunque".

### 3.4 Mail con cluster assegnato vs mail senza cluster

Comando: `python -m src.queries.mail <mail_id>`.

**Mail con cluster** (`EFTA01998334-0`, la stessa incontrata al §2.1):

```
Info mail:
{'id': 'EFTA01998334-0', 'subject': 'Barbro Ehnbom', 'sent_at': '2012-07-31T01:45:11+00:00',
 'redaction_count': 2, 'redaction_ratio': 0.0034, 'attachment_count': 0, 'is_promotional': False,
 'cluster_id': 52, 'label': 'BBB', 'probability': 1.0}
```

**Mail senza cluster** (`001df92b110e9da90631a66cf97a0a11`, individuata con
`MATCH (m:Mail) WHERE NOT (m)-[:BELONGS_TO]->() RETURN m.id LIMIT 1`):

```
Info mail:
{'id': '001df92b110e9da90631a66cf97a0a11', 'subject': 'Re:', 'sent_at': '2007-02-19T20:50:39+00:00',
 'redaction_count': 0, 'redaction_ratio': 0.0, 'attachment_count': 0, 'is_promotional': False,
 'cluster_id': None, 'label': None, 'probability': None}
```

`get_mail_info` (`src/queries/mail.py`, `GET_MAIL_INFO_QUERY`) usa
`OPTIONAL MATCH` sulla relazione `BELONGS_TO`: quando manca, `cluster_id`,
`label` e `probability` valgono semplicemente `None` nel dizionario
risultato, senza eccezioni né rami di codice dedicati. Questo è il
comportamento atteso per il 54,53% delle mail prive di cluster (si veda la
sezione 4), non un caso anomalo da gestire a parte.

### 3.5 Esempi `curl` contro l'API reale (`http://localhost:8000`)

```
$ curl -s "http://localhost:8000/clusters/52/mails?limit=3"
[{"id":"EFTA01998334-0","subject":"Barbro Ehnbom","sent_at":"2012-07-31T01:45:11+00:00","redaction_count":2,"probability":1.0},
 {"id":"vol00009-efta01165804-pdf","subject":"Our new FEOY 2011 i Love & Kisses from Sth!!","sent_at":"2011-06-14T22:19:56+00:00","redaction_count":0,"probability":0.9080871343612671},
 {"id":"vol00009-efta01136076-pdf","subject":"SALSS 2013 Save the Date","sent_at":"2013-05-09T15:40:02+00:00","redaction_count":0,"probability":0.8999784588813782}]
```

```
$ curl -s "http://localhost:8000/mails/EFTA01998334-0"
{"id":"EFTA01998334-0","subject":"Barbro Ehnbom","sent_at":"2012-07-31T01:45:11+00:00","redaction_count":2,
 "redaction_ratio":0.003418803418803419,"attachment_count":0,"is_promotional":false,
 "cluster_id":52,"label":"BBB","probability":1.0}
```

```
$ curl -s "http://localhost:8000/persons/daphne%20wallace/mails?limit=3"
[{"id":"EFTA02221172-0","subject":"Re: Call List for JE-who is David Mapp?","sent_at":"2017-08-21T15:11:00+00:00"},
 {"id":"EFTA02221409-2","subject":"","sent_at":"2017-08-22T15:13:00+00:00"},
 {"id":"EFTA02222757-1","subject":"","sent_at":"2017-09-12T17:32:00+00:00"}]
```

```
$ curl -s "http://localhost:8000/clusters/top-redacted?limit=3"
[{"cluster_id":43,"label":"Epstein Case","total_redactions":4635},
 {"cluster_id":135,"label":"Private Matters","total_redactions":4455},
 {"cluster_id":222,"label":"Travel","total_redactions":3625}]
```

L'API restituisce esattamente gli stessi dati delle query Cypher
sottostanti (§3.1-3.3), serializzati in JSON dai router (`src/api/
routers/`), che a loro volta chiamano `src/crud/`/`src/queries/` senza
Cypher inline, come da convenzione del progetto.

## 4. Qualità e limiti del dato

Lo script di validazione post-import (`python -m src.cli validate`,
`src/etl/validate_import.py`, issue #10) misura quante entità mancano delle
relazioni "attese" nel grafo. Risultati completi, con spiegazione estesa
del perché ciascun numero è atteso e non un bug, in
`docs/validation_findings.md`. In sintesi:

| Metrica | Totale | Senza relazione attesa | Percentuale |
|---|---|---|---|
| `Mail` senza `SENT` in ingresso | 400.000 | 41.021 | 10,26% |
| `Mail` senza `BELONGS_TO` in uscita | 400.000 | 218.107 | 54,53% |
| `EmailAddress` senza `OWNS` in ingresso | 695.787 | 676.324 | 97,2% |

Le cause, coerenti con quanto documentato in `docs/validation_findings.md`:

- **Mail senza mittente identificato (10,26%)**: per una parte dei record
  sorgente il campo `sender` non era estraibile in modo affidabile (assente,
  malformato, o completamente redatto senza un indirizzo sintetico
  associabile). L'ETL non scarta comunque la mail: il nodo `Mail` esiste,
  solo privo dell'arco `SENT` in ingresso.
- **Mail senza cluster assegnato (54,53%)**: il clustering a monte è
  soft-clustering probabilistico, che per costruzione non assegna
  necessariamente ogni mail a un cluster con confidenza sufficiente. È un
  comportamento atteso dell'algoritmo di clustering, non un difetto
  dell'import (si veda anche l'esempio concreto al §3.4).
- **Indirizzi senza `Person` proprietaria (97,2%)**: per design, un
  `Person` — e quindi l'arco `OWNS` — si crea solo quando esiste almeno un
  display name risolvibile in modo deterministico (§1.4). Non c'è
  adjudication automatica sui casi ambigui residui. Con 695.787 indirizzi
  email a fronte di sole 2.585 `Person` risolte, la stragrande maggioranza
  degli indirizzi senza `Person` associata è la conseguenza numerica
  attesa di questa scelta di design, non un errore di risoluzione.

Nessuno di questi numeri richiede correzione: sono conseguenze dirette
delle regole ETL (parsing deterministico, entity resolution senza
adjudication automatica sui casi ambigui, soft-clustering a monte) applicate
a un dataset sorgente con dati mancanti, redatti o ambigui per costruzione.

## 5. Conteggi finali dell'import

Verificati dal vivo sul database Neo4j locale (`bd2-neopstein-neo4j-1`) con:

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS n ORDER BY label;
MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS n ORDER BY rel;
```

**Nodi:**

| Label | Conteggio |
|---|---|
| `Person` | 2.585 |
| `EmailAddress` | 695.787 |
| `Mail` | 400.000 |
| `Cluster` | 289 |
| `Thread` | 327.609 |

**Relazioni:**

| Tipo | Conteggio |
|---|---|
| `OWNS` | 19.463 |
| `SENT` | 358.979 |
| `TO` | 431.448 |
| `CC` | 61.935 |
| `BCC` | 295 |
| `BELONGS_TO` | 181.893 |
| `PART_OF` | 400.000 |

Tutti i conteggi coincidono con quelli attesi dai CSV sorgente (confrontati
da `verify_counts`, si veda `docs/validation_findings.md`): import
idempotente confermato coerente, nessun mismatch.

**Tempo di esecuzione dell'import**: 74,15 secondi per ~2,9M righe totali
tra nodi e relazioni. Cifra indicativa, riportata dalla PR di merge
dell'issue #6 (`feat(etl): import idempotente CSV -> Neo4j con verifica
conteggi`), non rieseguita in questa sede per non impattare il database
locale in uso attivo.
