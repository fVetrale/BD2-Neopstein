"""Costruzione dei CSV per l'import in Neo4j a partire dal parquet sorgente.

Legge il parquet con pyarrow (niente pandas, vedi CLAUDE.md), fa parsing
riga per riga con `clean_data.parse_recipient_field`, risolve le identità
Person con `entity_resolution.resolve_persons` (una sola volta su tutto il
dataset, dopo aver raccolto tutte le menzioni) e scrive i CSV per nodi e
relazioni in `data/processed/graph/`.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

import pyarrow.parquet as pq

from src.etl import entity_resolution
from src.etl.clean_data import parse_recipient_field

logger = logging.getLogger(__name__)

DEFAULT_PARQUET_PATH = Path("data/raw/jmail_emails_clustered_sample_thread_aware.parquet")
DEFAULT_OUTPUT_DIR = Path("data/processed/graph")

_RECIPIENT_FIELDS = ("to", "cc", "bcc")
_BATCH_SIZE = 10_000

_MAIL_COLUMNS = [
    "id",
    "doc_id",
    "message_index",
    "sender",
    "to_recipients",
    "cc_recipients",
    "bcc_recipients",
    "subject_clean",
    "content_clean",
    "sent_at_datetime",
    "redaction_count",
    "redaction_ratio",
    "attachment_count",
    "is_promotional",
    "epstein_is_sender",
    "cluster",
    "cluster_name",
    "cluster_prob",
]


def _parse_sender(raw_sender: str | None, mail_id: str) -> list[dict] | None:
    """Parsa il campo sender, None se il parsing fallisce (skip solo SENT).

    Oltre al caso documentato (sender JSON-parseable a int/float, TypeError
    in iterazione), esistono righe (~88/400000) in cui il JSON decodifica a
    una stringa nuda: in quel caso `parse_recipient_field` itererebbe sui
    singoli caratteri della stringa senza sollevare eccezioni, producendo
    entry spazzatura. Le trattiamo allo stesso modo (parsing fallito, skip
    della sola relazione SENT) con un pre-check esplicito.
    """
    if not raw_sender:
        return []
    try:
        decoded = json.loads(raw_sender)
    except json.JSONDecodeError:
        pass  # stringa non-JSON: gestita dal fallback interno di parse_recipient_field
    else:
        if not isinstance(decoded, list):
            return None

    try:
        return parse_recipient_field(raw_sender, mail_id, "sender")
    except TypeError:
        return None


def build_graph_csvs(
    parquet_path: Path | str = DEFAULT_PARQUET_PATH,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> dict:
    parquet_path = Path(parquet_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mails: list[dict] = []
    row_recipients: list[dict] = []  # allineato a mails: {"sender": ..., "to": ..., "cc": ..., "bcc": ...}
    addresses: dict[str, dict] = {}
    clusters: dict[int, str] = {}
    belongs_to: list[dict] = []
    threads: set[str] = set()
    part_of: list[dict] = []
    mentions: list[tuple[str, str]] = []
    epstein_sender_addresses: set[str] = set()

    rows_processed = 0
    sent_skipped_parse_failure = 0

    parquet_file = pq.ParquetFile(parquet_path)
    for batch in parquet_file.iter_batches(columns=_MAIL_COLUMNS, batch_size=_BATCH_SIZE):
        for row in batch.to_pylist():
            rows_processed += 1
            if rows_processed % 50_000 == 0:
                logger.info("parsing: %d righe processate", rows_processed)
            mail_id = row["id"]

            mails.append(
                {
                    "id": mail_id,
                    "subject": row["subject_clean"],
                    "body": row["content_clean"],
                    "sent_at": row["sent_at_datetime"].isoformat() if row["sent_at_datetime"] else None,
                    "redaction_count": row["redaction_count"],
                    "redaction_ratio": row["redaction_ratio"],
                    "attachment_count": row["attachment_count"],
                    "is_promotional": row["is_promotional"],
                }
            )

            sender_entries = _parse_sender(row["sender"], mail_id)
            if sender_entries is None:
                sent_skipped_parse_failure += 1
                sender_entries = []

            recipients = {"sender": sender_entries}
            for field, column in (
                ("to", "to_recipients"),
                ("cc", "cc_recipients"),
                ("bcc", "bcc_recipients"),
            ):
                recipients[field] = parse_recipient_field(row[column], mail_id, field)
            row_recipients.append(recipients)

            for field_entries in recipients.values():
                for entry in field_entries:
                    addresses.setdefault(
                        entry["address"],
                        {"address": entry["address"], "domain": entry["domain"], "is_redacted": entry["is_redacted"]},
                    )
                    if entry["name"] is not None:
                        mentions.append((entry["name"], entry["address"]))

            if row["epstein_is_sender"]:
                for entry in sender_entries:
                    epstein_sender_addresses.add(entry["address"])

            cluster_id = row["cluster"]
            if cluster_id != -1:
                clusters.setdefault(cluster_id, row["cluster_name"])
                belongs_to.append(
                    {"mail_id": mail_id, "cluster_id": cluster_id, "probability": row["cluster_prob"]}
                )

            doc_id = row["doc_id"]
            threads.add(doc_id)
            part_of.append({"mail_id": mail_id, "doc_id": doc_id, "position": row["message_index"]})

    resolution = entity_resolution.resolve_persons(mentions, epstein_sender_addresses=epstein_sender_addresses)

    owns_pairs: set[tuple[str, str]] = set()
    for name, address in mentions:
        person_id = resolution.raw_name_to_person_id.get(name)
        if person_id is not None:
            owns_pairs.add((person_id, address))

    sent_rows = []
    to_rows = []
    cc_rows = []
    bcc_rows = []
    for mail, recipients in zip(mails, row_recipients):
        mail_id = mail["id"]
        for entry in recipients["sender"]:
            sent_rows.append({"address": entry["address"], "mail_id": mail_id})
        for entry in recipients["to"]:
            to_rows.append({"mail_id": mail_id, "address": entry["address"]})
        for entry in recipients["cc"]:
            cc_rows.append({"mail_id": mail_id, "address": entry["address"]})
        for entry in recipients["bcc"]:
            bcc_rows.append({"mail_id": mail_id, "address": entry["address"]})

    _write_csv(output_dir / "persons.csv", ["person_id", "display_name", "is_unknown", "is_epstein"], (
        {
            "person_id": p.person_id,
            "display_name": p.display_name,
            "is_unknown": p.is_unknown,
            "is_epstein": p.is_epstein,
        }
        for p in resolution.persons
    ))
    _write_csv(output_dir / "email_addresses.csv", ["address", "domain", "is_redacted"], addresses.values())
    _write_csv(
        output_dir / "mails.csv",
        ["id", "subject", "body", "sent_at", "redaction_count", "redaction_ratio", "attachment_count", "is_promotional"],
        mails,
    )
    _write_csv(output_dir / "clusters.csv", ["cluster_id", "label"], (
        {"cluster_id": cid, "label": label} for cid, label in clusters.items()
    ))
    _write_csv(output_dir / "threads.csv", ["doc_id"], ({"doc_id": d} for d in threads))
    _write_csv(output_dir / "owns.csv", ["person_id", "address"], (
        {"person_id": pid, "address": addr} for pid, addr in owns_pairs
    ))
    _write_csv(output_dir / "sent.csv", ["address", "mail_id"], sent_rows)
    _write_csv(output_dir / "to.csv", ["mail_id", "address"], to_rows)
    _write_csv(output_dir / "cc.csv", ["mail_id", "address"], cc_rows)
    _write_csv(output_dir / "bcc.csv", ["mail_id", "address"], bcc_rows)
    _write_csv(output_dir / "belongs_to.csv", ["mail_id", "cluster_id", "probability"], belongs_to)
    _write_csv(output_dir / "part_of.csv", ["mail_id", "doc_id", "position"], part_of)

    counts = {
        "rows_processed": rows_processed,
        "mails": len(mails),
        "persons": len(resolution.persons),
        "email_addresses": len(addresses),
        "clusters": len(clusters),
        "threads": len(threads),
        "sent_rows": len(sent_rows),
        "sent_skipped_parse_failure": sent_skipped_parse_failure,
        "resolved_by_rules": resolution.resolved_by_rules,
        "is_unknown": resolution.is_unknown,
    }
    _print_report(counts)
    return counts


def _write_csv(path: Path, fieldnames: list[str], rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _print_report(counts: dict) -> None:
    print("=== build_graph_csvs report ===")
    print(f"rows processed:              {counts['rows_processed']}")
    print(f"mails:                       {counts['mails']}")
    print(f"email addresses:             {counts['email_addresses']}")
    print(f"clusters (excl. -1):         {counts['clusters']}")
    print(f"threads:                     {counts['threads']}")
    print(f"SENT rows written:           {counts['sent_rows']}")
    print(f"SENT rows skipped (parse):   {counts['sent_skipped_parse_failure']}")
    print("--- entity resolution ---")
    print(f"persons (total):             {counts['persons']}")
    print(f"resolved by rules:           {counts['resolved_by_rules']}")
    print(f"is_unknown:                  {counts['is_unknown']}")
