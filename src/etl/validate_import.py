"""Verifica di cardinalità/integrità referenziale post-import.

Complementare a `verify_counts` (`src/etl/import_data.py`, confronto conteggi
CSV vs Neo4j): qui si controlla invece quante `Mail`/`EmailAddress` mancano di
relazioni attese (`SENT`, `BELONGS_TO`, `OWNS`). Numeri "bassi" non sono errori:
sono caratteristiche note del dataset, documentate in `docs/validation_findings.md`.
"""

from __future__ import annotations

from neo4j import Driver

# (chiave del dict dei risultati -> query Cypher di conteggio mirata)
_INTEGRITY_QUERIES: dict[str, str] = {
    "mail_total": "MATCH (m:Mail) RETURN count(m) AS c",
    "mail_without_sent": "MATCH (m:Mail) WHERE NOT EXISTS { ()-[:SENT]->(m) } RETURN count(m) AS c",
    "mail_without_belongs_to": "MATCH (m:Mail) WHERE NOT EXISTS { (m)-[:BELONGS_TO]->() } RETURN count(m) AS c",
    "email_address_total": "MATCH (e:EmailAddress) RETURN count(e) AS c",
    "email_address_without_owns": "MATCH (e:EmailAddress) WHERE NOT EXISTS { ()-[:OWNS]->(e) } RETURN count(e) AS c",
}


def _pct(part: int, total: int) -> float:
    """Percentuale di `part` su `total`, arrotondata a 2 decimali.

    Ritorna 0.0 se `total` è zero, senza sollevare eccezioni.
    """
    if total == 0:
        return 0.0
    return round(100 * part / total, 2)


def check_graph_integrity(driver: Driver) -> dict:
    """Calcola cardinalità/integrità referenziale del grafo attualmente in Neo4j.

    Esegue query Cypher mirate (una per metrica, non un'unica query monolitica
    con `WITH` concatenati su match non correlati). Non solleva eccezioni per
    numeri "bassi": sono dati attesi, non errori.

    Ritorna un dict con conteggi assoluti e percentuali per `Mail` (mail senza
    `SENT` in ingresso, mail senza `BELONGS_TO` in uscita) e `EmailAddress`
    (indirizzi senza `OWNS` in ingresso).
    """
    counts: dict[str, int] = {}
    with driver.session() as session:
        for key, query in _INTEGRITY_QUERIES.items():
            counts[key] = session.run(query).single()["c"]

    mail_total = counts["mail_total"]
    email_address_total = counts["email_address_total"]

    return {
        "mail": {
            "total": mail_total,
            "without_sent": counts["mail_without_sent"],
            "without_sent_pct": _pct(counts["mail_without_sent"], mail_total),
            "without_belongs_to": counts["mail_without_belongs_to"],
            "without_belongs_to_pct": _pct(counts["mail_without_belongs_to"], mail_total),
        },
        "email_address": {
            "total": email_address_total,
            "without_owns": counts["email_address_without_owns"],
            "without_owns_pct": _pct(counts["email_address_without_owns"], email_address_total),
        },
    }


def format_integrity_report(results: dict) -> str:
    """Formatta il dict di `check_graph_integrity` in un report testuale leggibile."""
    mail = results["mail"]
    email_address = results["email_address"]

    lines = [
        "=== Report integrità grafo (cardinalità) ===",
        "",
        "Mail:",
        f"  totale: {mail['total']}",
        f"  senza SENT in ingresso: {mail['without_sent']} ({mail['without_sent_pct']}%)",
        f"  senza BELONGS_TO in uscita: {mail['without_belongs_to']} ({mail['without_belongs_to_pct']}%)",
        "",
        "EmailAddress:",
        f"  totale: {email_address['total']}",
        f"  senza OWNS in ingresso: {email_address['without_owns']} ({email_address['without_owns_pct']}%)",
    ]
    return "\n".join(lines)
