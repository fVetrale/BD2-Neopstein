"""Query di lettura sui `Cluster` del grafo email.

Ogni funzione accetta una `neo4j.Session` già aperta (mai costruisce il
driver internamente, tranne nel blocco `__main__`) ed esegue una singola
query Cypher in sola lettura, restituendo una lista di dizionari "piatti"
pronta per essere serializzata (es. da un router FastAPI).
"""

from __future__ import annotations

import argparse
import logging
import os
from pprint import pprint

from neo4j import GraphDatabase, Session

logger = logging.getLogger(__name__)


def get_cluster_mails(session: Session, cluster_id: int) -> list[dict]:
    """Ritorna le `Mail` appartenenti al `Cluster` con `cluster_id` dato.

    Ogni riga contiene le proprietà rilevanti della Mail più `probability`
    della relazione `BELONGS_TO`. Se il cluster non esiste o non ha mail
    collegate, ritorna una lista vuota (nessuna eccezione).
    """
    query = (
        "MATCH (m:Mail)-[r:BELONGS_TO]->(c:Cluster {cluster_id: $cluster_id}) "
        "RETURN m.id AS id, m.subject AS subject, m.sent_at AS sent_at, "
        "m.redaction_count AS redaction_count, r.probability AS probability"
    )
    result = session.run(query, cluster_id=cluster_id)
    return [record.data() for record in result]


def get_cluster_persons(session: Session, cluster_id: int) -> list[dict]:
    """Ritorna le `Person` distinte coinvolte nelle mail del cluster dato.

    Risale da `EmailAddress` a `Person` tramite `OWNS`, considerando sia i
    mittenti (`SENT`) sia i destinatari (`TO|CC|BCC`) delle mail del
    cluster. Indirizzi senza `Person` associata vengono semplicemente
    esclusi dal risultato.
    """
    query = (
        "MATCH (m:Mail)-[:BELONGS_TO]->(:Cluster {cluster_id: $cluster_id}) "
        "MATCH (e:EmailAddress)-[:SENT|TO|CC|BCC]-(m) "
        "MATCH (p:Person)-[:OWNS]->(e) "
        "RETURN DISTINCT p.person_id AS person_id, p.display_name AS display_name, "
        "p.is_unknown AS is_unknown, p.is_epstein AS is_epstein"
    )
    result = session.run(query, cluster_id=cluster_id)
    return [record.data() for record in result]


def get_top_redacted_clusters(session: Session, limit: int = 10) -> list[dict]:
    """Ritorna i `Cluster` con più redazioni totali sulle proprie mail.

    Somma `redaction_count` (trattando i valori null come 0) su tutte le
    `Mail` collegate a ciascun `Cluster` tramite `BELONGS_TO`, ordina in
    modo decrescente sulla somma e applica `limit`.
    """
    query = (
        "MATCH (m:Mail)-[:BELONGS_TO]->(c:Cluster) "
        "RETURN c.cluster_id AS cluster_id, c.label AS label, "
        "sum(coalesce(m.redaction_count, 0)) AS total_redactions "
        "ORDER BY total_redactions DESC "
        "LIMIT $limit"
    )
    result = session.run(query, limit=limit)
    return [record.data() for record in result]


def _pick_sample_cluster_id(session: Session) -> int | None:
    """Recupera un `cluster_id` esistente dal DB, o `None` se non ce n'è."""
    result = session.run("MATCH (c:Cluster) RETURN c.cluster_id AS cluster_id LIMIT 1")
    record = result.single()
    return record["cluster_id"] if record is not None else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="src.queries.cluster")
    parser.add_argument("--cluster-id", type=int, default=None, help="cluster_id da interrogare (default: il primo trovato nel DB)")
    parser.add_argument("--limit", type=int, default=10, help="numero massimo di cluster nella classifica redazioni (default: 10)")
    args = parser.parse_args()

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    try:
        with driver.session() as session:
            cluster_id = args.cluster_id
            if cluster_id is None:
                cluster_id = _pick_sample_cluster_id(session)

            if cluster_id is None:
                logger.warning("Nessun Cluster presente nel DB: salto le query dipendenti da cluster_id")
            else:
                print(f"--- Mail del cluster {cluster_id} ---")
                pprint(get_cluster_mails(session, cluster_id))

                print(f"--- Persone coinvolte nel cluster {cluster_id} ---")
                pprint(get_cluster_persons(session, cluster_id))

            print(f"--- Top {args.limit} cluster per redazioni totali ---")
            pprint(get_top_redacted_clusters(session, limit=args.limit))
    finally:
        driver.close()
