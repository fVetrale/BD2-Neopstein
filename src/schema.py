"""Constraint e indici Neo4j per il modello a grafo.

Applica lo schema (unique constraint sulle chiavi dei nodi e indici sugli
attributi usati nei filtri) tramite Cypher `IF NOT EXISTS`, quindi in modo
idempotente. Nessun dato viene letto o scritto qui: solo definizione dello
schema, da eseguire PRIMA di qualsiasi import di CSV (`import_data.py`).
"""

from __future__ import annotations

import logging

from neo4j import Driver, Session

logger = logging.getLogger(__name__)

# (nome, statement) per i unique constraint su ciascuna chiave di nodo.
CONSTRAINTS: list[tuple[str, str]] = [
    (
        "person_id_unique",
        "CREATE CONSTRAINT person_id_unique IF NOT EXISTS "
        "FOR (p:Person) REQUIRE p.person_id IS UNIQUE",
    ),
    (
        "email_address_unique",
        "CREATE CONSTRAINT email_address_unique IF NOT EXISTS "
        "FOR (e:EmailAddress) REQUIRE e.address IS UNIQUE",
    ),
    (
        "mail_id_unique",
        "CREATE CONSTRAINT mail_id_unique IF NOT EXISTS "
        "FOR (m:Mail) REQUIRE m.id IS UNIQUE",
    ),
    (
        "cluster_id_unique",
        "CREATE CONSTRAINT cluster_id_unique IF NOT EXISTS "
        "FOR (c:Cluster) REQUIRE c.cluster_id IS UNIQUE",
    ),
    (
        "thread_doc_id_unique",
        "CREATE CONSTRAINT thread_doc_id_unique IF NOT EXISTS "
        "FOR (t:Thread) REQUIRE t.doc_id IS UNIQUE",
    ),
]

# (nome, statement) per gli indici non-unique sugli attributi filtrati.
INDEXES: list[tuple[str, str]] = [
    (
        "mail_sent_at_index",
        "CREATE INDEX mail_sent_at_index IF NOT EXISTS "
        "FOR (m:Mail) ON (m.sent_at)",
    ),
    (
        "email_address_domain_index",
        "CREATE INDEX email_address_domain_index IF NOT EXISTS "
        "FOR (e:EmailAddress) ON (e.domain)",
    ),
]


def apply_schema(session: Session) -> None:
    """Applica tutti i constraint e gli indici tramite la sessione data.

    Idempotente grazie a `IF NOT EXISTS`: può essere rieseguita più volte
    senza errori né effetti collaterali aggiuntivi.
    """
    for name, statement in CONSTRAINTS:
        logger.info("Applico constraint: %s", name)
        session.run(statement)

    for name, statement in INDEXES:
        logger.info("Applico indice: %s", name)
        session.run(statement)

    logger.info(
        "Schema applicato: %d constraint, %d indici", len(CONSTRAINTS), len(INDEXES)
    )


def apply_schema_with_driver(driver: Driver) -> None:
    """Apre una sessione dal driver dato e applica lo schema."""
    with driver.session() as session:
        apply_schema(session)
