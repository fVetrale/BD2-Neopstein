# Guida demo: API + Neo4j

Parametri reali (presi dal grafo già importato) e query Cypher gemelle per
mostrare in Neo4j Browser lo stesso sottografo restituito da ciascuna API.
Tutti i valori sono stati verificati contro un'istanza in esecuzione
(`docker compose up -d neo4j api`) e non sono placeholder.

- API base URL: `http://localhost:8000` — Swagger UI interattiva su
  `http://localhost:8000/docs`
- Neo4j Browser: `http://localhost:7474` (auth: vedi `.env`, `NEO4J_AUTH`)

Le query Cypher sono scritte in forma `MATCH path = (...) RETURN path` (non
tabellare) apposta per la visualizzazione a grafo del Browser.

---

## Mails

Mail scelta: **`vol00009-efta00082000-pdf`** — "RE: URGENT-Ghislaine Maxwell
02879-509 - COURT ORDER", nel cluster 43 ("Epstein Case"), con mittente,
destinatari TO/CC/BCC e 3 `Person` risolte (compresa `jeffrey e`).

### `GET /mails/{id}`
```
curl http://localhost:8000/mails/vol00009-efta00082000-pdf
```
Mostra le proprietà della mail e il cluster/probability collegati.

```cypher
MATCH path = (m:Mail {id: 'vol00009-efta00082000-pdf'})-[:BELONGS_TO]->(:Cluster)
RETURN path
```

### `GET /mails/{id}/persons`
```
curl http://localhost:8000/mails/vol00009-efta00082000-pdf/persons
```
Restituisce 3 persone (sender/to/cc) — nota anche il destinatario BCC
completamente redatto, escluso qui perché senza `Person` associata.

```cypher
MATCH (m:Mail {id: 'vol00009-efta00082000-pdf'})
MATCH addr = (ea:EmailAddress)-[:SENT|TO|CC|BCC]-(m)
OPTIONAL MATCH owner = (:Person)-[:OWNS]->(ea)
RETURN addr, owner
```

### `POST /mails` → `PUT /mails/{id}` → `DELETE /mails/{id}`
Ciclo CRUD dal vivo su un id sintetico (`demo-mail-001`), mai su dati reali.
Eseguire nell'ordine durante la demo:

```
curl -X POST http://localhost:8000/mails \
  -H "Content-Type: application/json" \
  -d '{"id":"demo-mail-001","subject":"Demo Subject","sent_at":"2026-07-26T10:00:00+00:00","redaction_count":0,"redaction_ratio":0.0,"attachment_count":0,"is_promotional":false}'
# 201

curl -X PUT http://localhost:8000/mails/demo-mail-001 \
  -H "Content-Type: application/json" \
  -d '{"subject":"Demo Subject Updated"}'
# 200

curl -X DELETE http://localhost:8000/mails/demo-mail-001
# 204
```

```cypher
-- eseguire dopo la POST/PUT per vederlo comparire/cambiare, dopo la DELETE per vederlo sparire
MATCH (m:Mail {id: 'demo-mail-001'}) RETURN m
```

---

## Persons

Persona scelta: **`noam chomsky`** (Noam Chomsky) — 58 indirizzi, 73 mail
inviate, 39 ricevute, 9 persone connesse tra cui `jeffrey e` e la moglie
`valeria chomsky`. Buon caso perché mescola indirizzi reali (`chomsky@mit.edu`)
e destinatari completamente redatti.

> Nota: il `person_id` contiene uno spazio → nell'URL va URL-encoded
> (`noam%20chomsky`).

### `GET /persons/{id}`
```
curl http://localhost:8000/persons/noam%20chomsky
```
```cypher
MATCH (p:Person {person_id: 'noam chomsky'}) RETURN p
```

### `GET /persons/{id}/mails`
```
curl "http://localhost:8000/persons/noam%20chomsky/mails?limit=10"
```
```cypher
MATCH path = (p:Person {person_id: 'noam chomsky'})-[:OWNS]->(:EmailAddress)-[:SENT|TO|CC|BCC]-(:Mail)
RETURN path LIMIT 25
```

### `GET /persons/{id}/connected`
```
curl http://localhost:8000/persons/noam%20chomsky/connected
```
Mostra le 9 persone connesse via scambio email (incl. `jeffrey e`).
```cypher
MATCH path = (p:Person {person_id: 'noam chomsky'})-[:OWNS]->(:EmailAddress)-[:SENT]->(:Mail)-[:TO|CC|BCC]->(:EmailAddress)<-[:OWNS]-(:Person)
RETURN path LIMIT 25
```

### `GET /persons/{id}/addresses`
```
curl "http://localhost:8000/persons/noam%20chomsky/addresses?limit=10"
```
```cypher
MATCH path = (p:Person {person_id: 'noam chomsky'})-[:OWNS]->(:EmailAddress)
RETURN path LIMIT 25
```

### `POST /persons` → `PUT /persons/{id}` → `DELETE /persons/{id}`
Ciclo CRUD su id sintetico (`demo-person-001`):

```
curl -X POST http://localhost:8000/persons \
  -H "Content-Type: application/json" \
  -d '{"person_id":"demo-person-001","display_name":"Demo Person","is_unknown":false,"is_epstein":false}'
# 201

curl -X PUT http://localhost:8000/persons/demo-person-001 \
  -H "Content-Type: application/json" \
  -d '{"display_name":"Demo Person Updated"}'
# 200

curl -X DELETE http://localhost:8000/persons/demo-person-001
# 204
```

```cypher
MATCH (p:Person {person_id: 'demo-person-001'}) RETURN p
```

---

## Clusters

Cluster scelto: **`43`** — "Epstein Case", primo in classifica redazioni
(4635 redazioni totali), 6829 mail, 402 persone coinvolte.

### `GET /clusters/top-redacted`
```
curl "http://localhost:8000/clusters/top-redacted?limit=5"
```
Aggregazione (somma redazioni per cluster): per natura è tabellare, non un
pattern a grafo — mostrarla nel Browser in modalità tabella/testo.
```cypher
MATCH (m:Mail)-[:BELONGS_TO]->(c:Cluster)
RETURN c.cluster_id AS cluster_id, c.label AS label,
       sum(coalesce(m.redaction_count, 0)) AS total_redactions
ORDER BY total_redactions DESC LIMIT 5
```

### `GET /clusters/{id}`
```
curl http://localhost:8000/clusters/43
```
```cypher
MATCH (c:Cluster {cluster_id: 43}) RETURN c
```

### `GET /clusters/{id}/mails`
```
curl "http://localhost:8000/clusters/43/mails?limit=10"
```
```cypher
MATCH path = (:Mail)-[:BELONGS_TO]->(c:Cluster {cluster_id: 43})
RETURN path LIMIT 25
```

### `GET /clusters/{id}/persons`
```
curl "http://localhost:8000/clusters/43/persons?limit=10"
```
Query limitata a 25 mail del cluster per restare leggibile nel Browser
(il cluster ne ha 6829).
```cypher
MATCH (m:Mail)-[:BELONGS_TO]->(c:Cluster {cluster_id: 43})
WITH m, c LIMIT 25
MATCH path = (:Person)-[:OWNS]->(:EmailAddress)-[:SENT|TO|CC|BCC]-(m)
RETURN path, c
```

### `POST /clusters` → `PUT /clusters/{id}` → `DELETE /clusters/{id}`
Ciclo CRUD su id sintetico (`cluster_id: 999001`):

```
curl -X POST http://localhost:8000/clusters \
  -H "Content-Type: application/json" \
  -d '{"cluster_id":999001,"label":"Demo Cluster"}'
# 201

curl -X PUT http://localhost:8000/clusters/999001 \
  -H "Content-Type: application/json" \
  -d '{"label":"Demo Cluster Updated"}'
# 200

curl -X DELETE http://localhost:8000/clusters/999001
# 204
```

```cypher
MATCH (c:Cluster {cluster_id: 999001}) RETURN c
```

---

## Checklist rapida pre-demo
1. `docker compose up -d neo4j api`
2. Aprire `http://localhost:8000/docs` (Swagger) e `http://localhost:7474`
   (Neo4j Browser) in due tab.
3. Tutti gli id sopra sono già verificati contro l'istanza corrente; se il
   DB viene reimportato da zero, ri-verificarli (gli id sintetici demo-* non
   esistono per costruzione, quindi il ciclo CRUD funziona sempre).
