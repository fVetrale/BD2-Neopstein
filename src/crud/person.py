"""CRUD sulle proprietà del nodo `Person`.

Ogni funzione riceve una `neo4j.Session` già aperta e ritorna dict/None,
senza mai sollevare eccezioni HTTP (compito dei router). Il `create` usa
`CREATE` (non `MERGE`): se `person_id` esiste già, il constraint unique su
`Person.person_id` (`src/schema.py`) fa propagare
`neo4j.exceptions.ConstraintError`, che questa funzione NON cattura.
"""

from __future__ import annotations

from neo4j import Session

CREATE_PERSON_QUERY = """
CREATE (p:Person $props)
RETURN p.person_id AS person_id, p.display_name AS display_name,
       p.is_unknown AS is_unknown, p.is_epstein AS is_epstein
"""

GET_PERSON_QUERY = """
MATCH (p:Person {person_id: $person_id})
RETURN p.person_id AS person_id, p.display_name AS display_name,
       p.is_unknown AS is_unknown, p.is_epstein AS is_epstein
"""

UPDATE_PERSON_QUERY = """
MATCH (p:Person {person_id: $person_id})
SET p += $props
RETURN p.person_id AS person_id, p.display_name AS display_name,
       p.is_unknown AS is_unknown, p.is_epstein AS is_epstein
"""

DELETE_PERSON_QUERY = """
MATCH (p:Person {person_id: $person_id})
DETACH DELETE p
RETURN count(p) AS deleted
"""


def create_person(session: Session, data: dict) -> dict:
    """Crea una `Person` con le proprietà date (incluso `person_id`).

    Propaga `neo4j.exceptions.ConstraintError` se `person_id` esiste già.
    """
    result = session.run(CREATE_PERSON_QUERY, props=data)
    return result.single().data()


def get_person(session: Session, person_id: str) -> dict | None:
    """Ritorna le proprietà della `Person` con `person_id` dato, o `None`."""
    record = session.run(GET_PERSON_QUERY, person_id=person_id).single()
    return record.data() if record is not None else None


def update_person(session: Session, person_id: str, data: dict) -> dict | None:
    """Aggiorna le proprietà fornite (già filtrate dei campi non impostati) sulla `Person` data.

    `data` deve contenere solo i campi effettivamente forniti dal client
    (convenzione: il router filtra con `model_dump(exclude_unset=True)`
    prima di chiamare questa funzione). Ritorna `None` se `person_id` non esiste.
    """
    record = session.run(UPDATE_PERSON_QUERY, person_id=person_id, props=data).single()
    return record.data() if record is not None else None


def delete_person(session: Session, person_id: str) -> bool:
    """Elimina (con `DETACH DELETE`) la `Person` con `person_id` dato.

    Ritorna `True` se un nodo è stato trovato ed eliminato, `False` altrimenti.
    """
    record = session.run(DELETE_PERSON_QUERY, person_id=person_id).single()
    return bool(record["deleted"]) if record is not None else False
