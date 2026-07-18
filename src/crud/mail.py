"""CRUD sulle proprietà del nodo `Mail`.

Ogni funzione riceve una `neo4j.Session` già aperta e ritorna dict/None,
senza mai sollevare eccezioni HTTP (compito dei router). Il `create` usa
`CREATE` (non `MERGE`): se `id` esiste già, il constraint unique su
`Mail.id` (`src/schema.py`) fa propagare `neo4j.exceptions.ConstraintError`,
che questa funzione NON cattura.
"""

from __future__ import annotations

from neo4j import Session

CREATE_MAIL_QUERY = """
CREATE (m:Mail $props)
RETURN m.id AS id, m.subject AS subject, m.body AS body, m.sent_at AS sent_at,
       m.redaction_count AS redaction_count, m.redaction_ratio AS redaction_ratio,
       m.attachment_count AS attachment_count, m.is_promotional AS is_promotional
"""

GET_MAIL_QUERY = """
MATCH (m:Mail {id: $id})
RETURN m.id AS id, m.subject AS subject, m.body AS body, m.sent_at AS sent_at,
       m.redaction_count AS redaction_count, m.redaction_ratio AS redaction_ratio,
       m.attachment_count AS attachment_count, m.is_promotional AS is_promotional
"""

UPDATE_MAIL_QUERY = """
MATCH (m:Mail {id: $id})
SET m += $props
RETURN m.id AS id, m.subject AS subject, m.body AS body, m.sent_at AS sent_at,
       m.redaction_count AS redaction_count, m.redaction_ratio AS redaction_ratio,
       m.attachment_count AS attachment_count, m.is_promotional AS is_promotional
"""

DELETE_MAIL_QUERY = """
MATCH (m:Mail {id: $id})
DETACH DELETE m
RETURN count(m) AS deleted
"""


def create_mail(session: Session, data: dict) -> dict:
    """Crea una `Mail` con le proprietà date (incluso `id`).

    Propaga `neo4j.exceptions.ConstraintError` se `id` esiste già.
    """
    result = session.run(CREATE_MAIL_QUERY, props=data)
    return result.single().data()


def get_mail(session: Session, mail_id: str) -> dict | None:
    """Ritorna le proprietà della `Mail` con `id == mail_id`, o `None`."""
    record = session.run(GET_MAIL_QUERY, id=mail_id).single()
    return record.data() if record is not None else None


def update_mail(session: Session, mail_id: str, data: dict) -> dict | None:
    """Aggiorna le proprietà fornite (già filtrate dei campi non impostati) sulla `Mail` data.

    `data` deve contenere solo i campi effettivamente forniti dal client
    (convenzione: il router filtra con `model_dump(exclude_unset=True)`
    prima di chiamare questa funzione). Ritorna `None` se `mail_id` non esiste.
    """
    record = session.run(UPDATE_MAIL_QUERY, id=mail_id, props=data).single()
    return record.data() if record is not None else None


def delete_mail(session: Session, mail_id: str) -> bool:
    """Elimina (con `DETACH DELETE`) la `Mail` con `id == mail_id`.

    Ritorna `True` se un nodo è stato trovato ed eliminato, `False` altrimenti.
    """
    record = session.run(DELETE_MAIL_QUERY, id=mail_id).single()
    return bool(record["deleted"]) if record is not None else False
