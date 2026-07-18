"""CRUD sulle proprietà del nodo `Cluster`.

Ogni funzione riceve una `neo4j.Session` già aperta e ritorna dict/None,
senza mai sollevare eccezioni HTTP (compito dei router). Il `create` usa
`CREATE` (non `MERGE`): se `cluster_id` esiste già, il constraint unique su
`Cluster.cluster_id` (`src/schema.py`) fa propagare
`neo4j.exceptions.ConstraintError`, che questa funzione NON cattura.
"""

from __future__ import annotations

from neo4j import Session

CREATE_CLUSTER_QUERY = """
CREATE (c:Cluster $props)
RETURN c.cluster_id AS cluster_id, c.label AS label
"""

GET_CLUSTER_QUERY = """
MATCH (c:Cluster {cluster_id: $cluster_id})
RETURN c.cluster_id AS cluster_id, c.label AS label
"""

UPDATE_CLUSTER_QUERY = """
MATCH (c:Cluster {cluster_id: $cluster_id})
SET c += $props
RETURN c.cluster_id AS cluster_id, c.label AS label
"""

DELETE_CLUSTER_QUERY = """
MATCH (c:Cluster {cluster_id: $cluster_id})
DETACH DELETE c
RETURN count(c) AS deleted
"""


def create_cluster(session: Session, data: dict) -> dict:
    """Crea un `Cluster` con le proprietà date (incluso `cluster_id`).

    Propaga `neo4j.exceptions.ConstraintError` se `cluster_id` esiste già.
    """
    result = session.run(CREATE_CLUSTER_QUERY, props=data)
    return result.single().data()


def get_cluster(session: Session, cluster_id: int) -> dict | None:
    """Ritorna le proprietà del `Cluster` con `cluster_id` dato, o `None`."""
    record = session.run(GET_CLUSTER_QUERY, cluster_id=cluster_id).single()
    return record.data() if record is not None else None


def update_cluster(session: Session, cluster_id: int, data: dict) -> dict | None:
    """Aggiorna le proprietà fornite (già filtrate dei campi non impostati) sul `Cluster` dato.

    `data` deve contenere solo i campi effettivamente forniti dal client
    (convenzione: il router filtra con `model_dump(exclude_unset=True)`
    prima di chiamare questa funzione). Ritorna `None` se `cluster_id` non esiste.
    """
    record = session.run(UPDATE_CLUSTER_QUERY, cluster_id=cluster_id, props=data).single()
    return record.data() if record is not None else None


def delete_cluster(session: Session, cluster_id: int) -> bool:
    """Elimina (con `DETACH DELETE`) il `Cluster` con `cluster_id` dato.

    Ritorna `True` se un nodo è stato trovato ed eliminato, `False` altrimenti.
    """
    record = session.run(DELETE_CLUSTER_QUERY, cluster_id=cluster_id).single()
    return bool(record["deleted"]) if record is not None else False
