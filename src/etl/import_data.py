"""Import dei CSV generati da `build_csv.py` in Neo4j.

Legge i CSV in `data/processed/csv/` a streaming (mai l'intero file in
memoria) e li importa a batch con query `UNWIND $rows AS row ...`.
Import idempotente: sempre `MERGE` sulle chiavi dei nodi/relazioni, mai
`CREATE` puro. Da eseguire dopo `apply_schema_with_driver` (`src/schema.py`).
"""

from __future__ import annotations

import csv
import itertools
import logging
import time
from pathlib import Path
from typing import Callable, Iterator

from neo4j import Driver

from src.etl.build_csv import DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)

DEFAULT_CSV_DIR = DEFAULT_OUTPUT_DIR
DEFAULT_BATCH_SIZE = 5000


# --- coercizione tipi -------------------------------------------------------


def _to_bool(s: str) -> bool:
    return s == "True"


def _to_int(s: str) -> int:
    return int(s)


def _to_float(s: str) -> float:
    return float(s)


# --- lettura CSV a streaming -------------------------------------------------


def _read_rows(csv_path: Path, converters: dict[str, Callable[[str], object]]) -> Iterator[dict]:
    """Itera le righe del CSV applicando i converter di tipo indicati.

    Le colonne non presenti in `converters` restano stringhe così come
    scritte su disco (coerente con lo schema dei CSV).
    """
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for column, convert in converters.items():
                row[column] = convert(row[column])
            yield row


def _chunked(rows: Iterator[dict], batch_size: int) -> Iterator[list[dict]]:
    iterator = iter(rows)
    while True:
        chunk = list(itertools.islice(iterator, batch_size))
        if not chunk:
            return
        yield chunk


def _run_batched(
    driver: Driver,
    csv_path: Path,
    converters: dict[str, Callable[[str], object]],
    query: str,
    batch_size: int,
) -> int:
    """Esegue `query` con `UNWIND $rows` su ogni batch di righe del CSV.

    Ritorna il numero totale di righe processate.
    """
    total = 0
    with driver.session() as session:
        for chunk in _chunked(_read_rows(csv_path, converters), batch_size):
            session.run(query, rows=chunk)
            total += len(chunk)
    return total


# --- import nodi -------------------------------------------------------------


def import_persons(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MERGE (p:Person {person_id: row.person_id})
    SET p.display_name = row.display_name,
        p.is_unknown = row.is_unknown,
        p.is_epstein = row.is_epstein
    """
    converters = {"is_unknown": _to_bool, "is_epstein": _to_bool}
    return _run_batched(driver, Path(csv_dir) / "persons.csv", converters, query, batch_size)


def import_email_addresses(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MERGE (e:EmailAddress {address: row.address})
    SET e.domain = row.domain,
        e.is_redacted = row.is_redacted
    """
    converters = {"is_redacted": _to_bool}
    return _run_batched(driver, Path(csv_dir) / "email_addresses.csv", converters, query, batch_size)


def import_mails(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MERGE (m:Mail {id: row.id})
    SET m.subject = row.subject,
        m.body = row.body,
        m.sent_at = row.sent_at,
        m.redaction_count = row.redaction_count,
        m.redaction_ratio = row.redaction_ratio,
        m.attachment_count = row.attachment_count,
        m.is_promotional = row.is_promotional
    """
    converters = {
        "redaction_count": _to_int,
        "redaction_ratio": _to_float,
        "attachment_count": _to_int,
        "is_promotional": _to_bool,
    }
    return _run_batched(driver, Path(csv_dir) / "mails.csv", converters, query, batch_size)


def import_clusters(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MERGE (c:Cluster {cluster_id: row.cluster_id})
    SET c.label = row.label
    """
    converters = {"cluster_id": _to_int}
    return _run_batched(driver, Path(csv_dir) / "clusters.csv", converters, query, batch_size)


def import_threads(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MERGE (t:Thread {doc_id: row.doc_id})
    """
    return _run_batched(driver, Path(csv_dir) / "threads.csv", {}, query, batch_size)


# --- import relazioni ---------------------------------------------------------


def import_owns(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MATCH (p:Person {person_id: row.person_id})
    MATCH (e:EmailAddress {address: row.address})
    MERGE (p)-[:OWNS]->(e)
    """
    return _run_batched(driver, Path(csv_dir) / "owns.csv", {}, query, batch_size)


def import_sent(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MATCH (e:EmailAddress {address: row.address})
    MATCH (m:Mail {id: row.mail_id})
    MERGE (e)-[:SENT]->(m)
    """
    return _run_batched(driver, Path(csv_dir) / "sent.csv", {}, query, batch_size)


def import_to(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MATCH (m:Mail {id: row.mail_id})
    MATCH (e:EmailAddress {address: row.address})
    MERGE (m)-[:TO]->(e)
    """
    return _run_batched(driver, Path(csv_dir) / "to.csv", {}, query, batch_size)


def import_cc(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MATCH (m:Mail {id: row.mail_id})
    MATCH (e:EmailAddress {address: row.address})
    MERGE (m)-[:CC]->(e)
    """
    return _run_batched(driver, Path(csv_dir) / "cc.csv", {}, query, batch_size)


def import_bcc(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MATCH (m:Mail {id: row.mail_id})
    MATCH (e:EmailAddress {address: row.address})
    MERGE (m)-[:BCC]->(e)
    """
    return _run_batched(driver, Path(csv_dir) / "bcc.csv", {}, query, batch_size)


def import_belongs_to(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MATCH (m:Mail {id: row.mail_id})
    MATCH (c:Cluster {cluster_id: row.cluster_id})
    MERGE (m)-[r:BELONGS_TO]->(c)
    SET r.probability = row.probability
    """
    converters = {"cluster_id": _to_int, "probability": _to_float}
    return _run_batched(driver, Path(csv_dir) / "belongs_to.csv", converters, query, batch_size)


def import_part_of(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    query = """
    UNWIND $rows AS row
    MATCH (m:Mail {id: row.mail_id})
    MATCH (t:Thread {doc_id: row.doc_id})
    MERGE (m)-[r:PART_OF]->(t)
    SET r.position = row.position
    """
    converters = {"position": _to_int}
    return _run_batched(driver, Path(csv_dir) / "part_of.csv", converters, query, batch_size)


# --- orchestrazione -----------------------------------------------------------

# Ordine di import: nodi prima, poi relazioni (gli endpoint devono esistere).
_NODE_IMPORTS: list[tuple[str, Callable]] = [
    ("persons", import_persons),
    ("email_addresses", import_email_addresses),
    ("mails", import_mails),
    ("clusters", import_clusters),
    ("threads", import_threads),
]

_RELATIONSHIP_IMPORTS: list[tuple[str, Callable]] = [
    ("owns", import_owns),
    ("sent", import_sent),
    ("to", import_to),
    ("cc", import_cc),
    ("bcc", import_bcc),
    ("belongs_to", import_belongs_to),
    ("part_of", import_part_of),
]

# (chiave del dict dei conteggi -> nome file CSV senza estensione)
_CSV_FILE_BY_KEY: dict[str, str] = {
    "persons": "persons",
    "email_addresses": "email_addresses",
    "mails": "mails",
    "clusters": "clusters",
    "threads": "threads",
    "owns": "owns",
    "sent": "sent",
    "to": "to",
    "cc": "cc",
    "bcc": "bcc",
    "belongs_to": "belongs_to",
    "part_of": "part_of",
}

# (chiave del dict dei conteggi -> query Cypher di conteggio reale nel DB)
_COUNT_QUERY_BY_KEY: dict[str, str] = {
    "persons": "MATCH (p:Person) RETURN count(p) AS c",
    "email_addresses": "MATCH (e:EmailAddress) RETURN count(e) AS c",
    "mails": "MATCH (m:Mail) RETURN count(m) AS c",
    "clusters": "MATCH (c:Cluster) RETURN count(c) AS c",
    "threads": "MATCH (t:Thread) RETURN count(t) AS c",
    "owns": "MATCH ()-[r:OWNS]->() RETURN count(r) AS c",
    "sent": "MATCH ()-[r:SENT]->() RETURN count(r) AS c",
    "to": "MATCH ()-[r:TO]->() RETURN count(r) AS c",
    "cc": "MATCH ()-[r:CC]->() RETURN count(r) AS c",
    "bcc": "MATCH ()-[r:BCC]->() RETURN count(r) AS c",
    "belongs_to": "MATCH ()-[r:BELONGS_TO]->() RETURN count(r) AS c",
    "part_of": "MATCH ()-[r:PART_OF]->() RETURN count(r) AS c",
}


def run_import(
    driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR, batch_size: int = DEFAULT_BATCH_SIZE
) -> dict[str, int]:
    """Importa tutti i CSV in Neo4j: prima i nodi, poi le relazioni.

    Ritorna il numero di righe processate per ciascuna entità/relazione.
    """
    csv_dir = Path(csv_dir)
    counts: dict[str, int] = {}

    start_total = time.perf_counter()

    for name, import_fn in _NODE_IMPORTS + _RELATIONSHIP_IMPORTS:
        start_phase = time.perf_counter()
        counts[name] = import_fn(driver, csv_dir=csv_dir, batch_size=batch_size)
        elapsed_phase = time.perf_counter() - start_phase
        logger.info("Import %s: %d righe in %.2fs", name, counts[name], elapsed_phase)

    elapsed_total = time.perf_counter() - start_total
    logger.info("Import completato in %.2fs: %s", elapsed_total, counts)

    return counts


# Relazioni senza property proprie: `MERGE` collassa righe duplicate del CSV
# sorgente in un solo arco, quindi il conteggio "atteso" corretto è quello
# delle righe distinte, non delle righe grezze.
_DEDUPE_KEYS: set[str] = {"owns", "sent", "to", "cc", "bcc"}


def expected_counts_from_csv(csv_dir: Path = DEFAULT_CSV_DIR) -> dict[str, int]:
    """Conta le righe di dati (esclusa l'header) di ciascun CSV atteso.

    Per le chiavi in `_DEDUPE_KEYS` (relazioni senza property, dove `MERGE`
    collassa duplicati esatti in un solo arco) conta le righe distinte
    invece delle righe grezze, per confrontarsi correttamente con il grafo
    reale.
    """
    csv_dir = Path(csv_dir)
    expected: dict[str, int] = {}
    for key, filename in _CSV_FILE_BY_KEY.items():
        path = csv_dir / f"{filename}.csv"
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # header
            if key in _DEDUPE_KEYS:
                expected[key] = len({tuple(row) for row in reader})
            else:
                expected[key] = sum(1 for _ in reader)
    return expected


def verify_counts(driver: Driver, csv_dir: Path = DEFAULT_CSV_DIR) -> dict[str, dict[str, int]]:
    """Confronta i conteggi attesi (da CSV) con quelli reali nel DB.

    Ritorna, per ciascuna chiave, `{"expected": N, "actual": M, "match": bool}`.
    """
    expected_counts = expected_counts_from_csv(csv_dir)
    results: dict[str, dict] = {}

    with driver.session() as session:
        for key, query in _COUNT_QUERY_BY_KEY.items():
            actual = session.run(query).single()["c"]
            expected = expected_counts[key]
            match = actual == expected
            results[key] = {"expected": expected, "actual": actual, "match": match}
            if match:
                logger.info("Conteggio ok per %s: %d", key, actual)
            else:
                logger.warning(
                    "Mismatch conteggio per %s: atteso %d, trovato %d", key, expected, actual
                )

    return results
