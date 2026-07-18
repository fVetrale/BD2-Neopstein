"""Query di lettura su Person / EmailAddress.

Ogni funzione riceve una `neo4j.Session` già aperta (nessun driver costruito
internamente) e ritorna una lista di dict pronta per essere serializzata o
stampata. La deduplica dei risultati (una persona può possedere più
`EmailAddress`, una `Mail` può coinvolgere più indirizzi della stessa persona)
avviene lato Cypher tramite `DISTINCT` sulla chiave logica dell'entità
ritornata (`m.id` per le mail, `p2.person_id` per le persone connesse), non
sulle righe grezze del pattern match.
"""

from __future__ import annotations

import json
import logging
import os
import sys

from neo4j import Session

logger = logging.getLogger(__name__)


def get_person_mails(session: Session, person_id: str) -> list[dict]:
    """Tutte le Mail inviate o ricevute (TO/CC/BCC) dalla Person data.

    Attraversa tutti gli EmailAddress posseduti (OWNS) dalla persona.
    Dedup per Mail.id: se la persona possiede più indirizzi coinvolti sulla
    stessa mail, questa compare una sola volta nel risultato.
    """
    query = """
    MATCH (p:Person {person_id: $person_id})-[:OWNS]->(e:EmailAddress)
    MATCH (e)-[:SENT]->(m:Mail)
    RETURN DISTINCT m.id AS id, m.subject AS subject, m.sent_at AS sent_at
    UNION
    MATCH (p:Person {person_id: $person_id})-[:OWNS]->(e:EmailAddress)
    MATCH (m:Mail)-[:TO|CC|BCC]->(e)
    RETURN DISTINCT m.id AS id, m.subject AS subject, m.sent_at AS sent_at
    """
    result = session.run(query, person_id=person_id)
    rows = [dict(record) for record in result]
    rows.sort(key=lambda row: row["id"])
    return rows


def get_person_addresses(session: Session, person_id: str) -> list[dict]:
    """Tutti gli EmailAddress posseduti (OWNS) dalla Person data."""
    query = """
    MATCH (p:Person {person_id: $person_id})-[:OWNS]->(e:EmailAddress)
    RETURN DISTINCT e.address AS address, e.domain AS domain, e.is_redacted AS is_redacted
    """
    result = session.run(query, person_id=person_id)
    rows = [dict(record) for record in result]
    rows.sort(key=lambda row: row["address"])
    return rows


def get_connected_persons(session: Session, person_id: str) -> list[dict]:
    """Tutte le Person distinte connesse via scambio di email con la Person data.

    Due persone sono connesse se una ha inviato e l'altra è tra TO/CC/BCC su
    almeno una Mail comune, in una direzione o nell'altra. Gli EmailAddress
    intermedi non vengono filtrati per `is_redacted`. Dedup su
    `Person.person_id`: la persona di partenza è esplicitamente esclusa dal
    risultato.
    """
    query = """
    MATCH (p:Person {person_id: $person_id})-[:OWNS]->(e:EmailAddress)-[:SENT]->(m:Mail)-[:TO|CC|BCC]->(e2:EmailAddress)<-[:OWNS]-(p2:Person)
    WHERE p2.person_id <> $person_id
    RETURN DISTINCT p2.person_id AS person_id, p2.display_name AS display_name
    UNION
    MATCH (p:Person {person_id: $person_id})-[:OWNS]->(e:EmailAddress)<-[:TO|CC|BCC]-(m:Mail)<-[:SENT]-(e2:EmailAddress)<-[:OWNS]-(p2:Person)
    WHERE p2.person_id <> $person_id
    RETURN DISTINCT p2.person_id AS person_id, p2.display_name AS display_name
    """
    result = session.run(query, person_id=person_id)
    rows = [dict(record) for record in result]
    rows.sort(key=lambda row: row["person_id"])
    return rows


if __name__ == "__main__":
    from neo4j import GraphDatabase

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if len(sys.argv) < 2:
        print("Uso: python -m src.queries.person <person_id>", file=sys.stderr)
        sys.exit(1)

    target_person_id = sys.argv[1]

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    try:
        with driver.session() as session:
            mails = get_person_mails(session, target_person_id)
            addresses = get_person_addresses(session, target_person_id)
            connected = get_connected_persons(session, target_person_id)

        print(f"--- Mail per person_id={target_person_id!r} ({len(mails)}) ---")
        print(json.dumps(mails, indent=2, default=str))
        print(f"--- EmailAddress per person_id={target_person_id!r} ({len(addresses)}) ---")
        print(json.dumps(addresses, indent=2, default=str))
        print(f"--- Person connesse a person_id={target_person_id!r} ({len(connected)}) ---")
        print(json.dumps(connected, indent=2, default=str))
    finally:
        driver.close()
