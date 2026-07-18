"""Query Cypher pronte all'uso per il nodo `Mail`.

Le funzioni ricevono una `neo4j.Session` già aperta e restituiscono strutture
dati Python semplici (dict/list), senza dipendenze da HTTP o dal driver.
"""

from __future__ import annotations

import argparse
import logging
import os

from neo4j import GraphDatabase, Session

logger = logging.getLogger(__name__)

GET_MAIL_INFO_QUERY = """
MATCH (m:Mail {id: $mail_id})
OPTIONAL MATCH (m)-[b:BELONGS_TO]->(c:Cluster)
RETURN m.id AS id, m.subject AS subject, m.sent_at AS sent_at,
       m.redaction_count AS redaction_count, m.redaction_ratio AS redaction_ratio,
       m.attachment_count AS attachment_count, m.is_promotional AS is_promotional,
       c.cluster_id AS cluster_id, c.label AS label, b.probability AS probability
"""

GET_MAIL_PERSONS_QUERY = """
MATCH (m:Mail {id: $mail_id})
CALL {
    WITH m
    MATCH (ea:EmailAddress)-[:SENT]->(m)
    RETURN ea, 'sender' AS role
    UNION
    WITH m
    MATCH (m)-[:TO]->(ea:EmailAddress)
    RETURN ea, 'to' AS role
    UNION
    WITH m
    MATCH (m)-[:CC]->(ea:EmailAddress)
    RETURN ea, 'cc' AS role
    UNION
    WITH m
    MATCH (m)-[:BCC]->(ea:EmailAddress)
    RETURN ea, 'bcc' AS role
}
MATCH (p:Person)-[:OWNS]->(ea)
RETURN p.person_id AS person_id, p.display_name AS display_name,
       p.is_unknown AS is_unknown, p.is_epstein AS is_epstein,
       collect(DISTINCT role) AS roles
ORDER BY person_id
"""


def get_mail_info(session: Session, mail_id: str) -> dict | None:
    """Restituisce le proprietà della `Mail` con `id == mail_id`.

    Include le info di cluster (`cluster_id`, `label`, `probability`) se la
    mail è collegata a un `Cluster` tramite `BELONGS_TO`; altrimenti quelle
    chiavi valgono `None`. Restituisce `None` se non esiste nessuna `Mail`
    con quell'id.
    """
    result = session.run(GET_MAIL_INFO_QUERY, mail_id=mail_id)
    record = result.single()
    if record is None:
        return None

    return {
        "id": record["id"],
        "subject": record["subject"],
        "sent_at": record["sent_at"],
        "redaction_count": record["redaction_count"],
        "redaction_ratio": record["redaction_ratio"],
        "attachment_count": record["attachment_count"],
        "is_promotional": record["is_promotional"],
        "cluster_id": record["cluster_id"],
        "label": record["label"],
        "probability": record["probability"],
    }


def get_mail_persons(session: Session, mail_id: str) -> list[dict]:
    """Restituisce le `Person` collegate alla mail (mittente e destinatari).

    Ogni persona è deduplicata per `person_id` e riporta i ruoli in cui
    compare rispetto alla mail (`sender`, `to`, `cc`, `bcc`). Restituisce
    lista vuota se `mail_id` non corrisponde a nessuna `Mail`.
    """
    result = session.run(GET_MAIL_PERSONS_QUERY, mail_id=mail_id)

    persons = []
    for record in result:
        persons.append(
            {
                "person_id": record["person_id"],
                "display_name": record["display_name"],
                "is_unknown": record["is_unknown"],
                "is_epstein": record["is_epstein"],
                "roles": sorted(record["roles"]),
            }
        )
    return persons


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="src.queries.mail")
    parser.add_argument("mail_id", nargs="?", default=None, help="Id della Mail da interrogare")
    args = parser.parse_args()

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    try:
        with driver.session() as session:
            mail_id = args.mail_id
            if mail_id is None:
                record = session.run("MATCH (m:Mail) RETURN m.id AS id LIMIT 1").single()
                if record is None:
                    raise SystemExit("Nessuna Mail trovata nel database")
                mail_id = record["id"]
                logger.info("Nessun mail_id fornito, uso il primo trovato: %s", mail_id)

            info = get_mail_info(session, mail_id)
            persons = get_mail_persons(session, mail_id)

            print("Info mail:")
            print(info)
            print("Persone collegate:")
            print(persons)
    finally:
        driver.close()
