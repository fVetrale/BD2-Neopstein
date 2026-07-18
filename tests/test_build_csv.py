import csv
import json
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from src.etl.build_csv import build_graph_csvs

_SCHEMA = pa.schema(
    [
        ("id", pa.large_string()),
        ("doc_id", pa.large_string()),
        ("message_index", pa.int64()),
        ("sender", pa.large_string()),
        ("to_recipients", pa.large_string()),
        ("cc_recipients", pa.large_string()),
        ("bcc_recipients", pa.large_string()),
        ("subject_clean", pa.large_string()),
        ("content_clean", pa.large_string()),
        ("sent_at_datetime", pa.timestamp("ns", tz="UTC")),
        ("redaction_count", pa.int64()),
        ("redaction_ratio", pa.float64()),
        ("attachment_count", pa.int64()),
        ("is_promotional", pa.bool_()),
        ("epstein_is_sender", pa.bool_()),
        ("cluster", pa.int64()),
        ("cluster_name", pa.large_string()),
        ("cluster_prob", pa.float32()),
    ]
)

_UTC = timezone.utc


def _write_parquet(tmp_path, rows):
    columns = {name: [row.get(name) for row in rows] for name in _SCHEMA.names}
    table = pa.table(columns, schema=_SCHEMA)
    path = tmp_path / "sample.parquet"
    pq.write_table(table, path)
    return path


def _read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _base_row(**overrides):
    row = {
        "id": "mail-x",
        "doc_id": "doc-x",
        "message_index": 0,
        "sender": None,
        "to_recipients": "[]",
        "cc_recipients": "[]",
        "bcc_recipients": "[]",
        "subject_clean": "subject",
        "content_clean": "body",
        "sent_at_datetime": datetime(2020, 1, 1, tzinfo=_UTC),
        "redaction_count": 0,
        "redaction_ratio": 0.0,
        "attachment_count": 0,
        "is_promotional": False,
        "epstein_is_sender": False,
        "cluster": -1,
        "cluster_name": None,
        "cluster_prob": None,
    }
    row.update(overrides)
    return row


def test_build_graph_csvs_end_to_end(tmp_path):
    rows = [
        _base_row(
            id="mail-1",
            doc_id="doc-1",
            message_index=0,
            sender="Alice One <alice@example.com>",
            to_recipients=json.dumps(["Bob Two <bob@example.org>"]),
            cluster=5,
            cluster_name="Cluster Five",
            cluster_prob=0.9,
        ),
        _base_row(
            id="mail-2",
            doc_id="doc-1",
            message_index=1,
            sender="Carol Three <carol@example.com>",
            to_recipients=json.dumps(["REDACTED"]),
            cluster=-1,
            cluster_name=None,
            cluster_prob=None,
        ),
        _base_row(
            id="mail-3",
            doc_id="doc-2",
            message_index=0,
            sender=None,
            to_recipients=json.dumps(["Dave Four <dave@example.org>"]),
            cluster=5,
            cluster_name="Cluster Five",
            cluster_prob=0.5,
        ),
    ]
    parquet_path = _write_parquet(tmp_path, rows)
    output_dir = tmp_path / "graph"

    counts = build_graph_csvs(parquet_path=parquet_path, output_dir=output_dir)

    assert counts["rows_processed"] == 3
    assert counts["mails"] == 3

    mails = _read_csv(output_dir / "mails.csv")
    assert {m["id"] for m in mails} == {"mail-1", "mail-2", "mail-3"}

    # Normale: Person + EmailAddress + Mail + SENT + TO
    addresses = _read_csv(output_dir / "email_addresses.csv")
    addr_by_key = {a["address"]: a for a in addresses}
    assert "alice@example.com" in addr_by_key
    assert addr_by_key["alice@example.com"]["is_redacted"] == "False"
    assert "bob@example.org" in addr_by_key

    sent_rows = _read_csv(output_dir / "sent.csv")
    assert {"address": "alice@example.com", "mail_id": "mail-1"} in sent_rows

    to_rows = _read_csv(output_dir / "to.csv")
    assert {"mail_id": "mail-1", "address": "bob@example.org"} in to_rows

    persons = _read_csv(output_dir / "persons.csv")
    display_names = {p["display_name"] for p in persons}
    assert "Alice One" in display_names
    assert "Bob Two" in display_names

    owns = _read_csv(output_dir / "owns.csv")
    alice_id = next(p["person_id"] for p in persons if p["display_name"] == "Alice One")
    assert {"person_id": alice_id, "address": "alice@example.com"} in owns

    # Redacted: nodo EmailAddress sintetico, relazione TO non scartata
    redacted_addresses = [a for a in addresses if a["is_redacted"] == "True"]
    assert len(redacted_addresses) == 1
    assert redacted_addresses[0]["address"] == "redacted:mail-2:to:0"
    to_mail_2 = [r for r in to_rows if r["mail_id"] == "mail-2"]
    assert to_mail_2 == [{"mail_id": "mail-2", "address": "redacted:mail-2:to:0"}]

    # Sender nullo: Mail creata, nessun SENT
    assert all(r["mail_id"] != "mail-3" for r in sent_rows)

    # cluster == -1: nessun BELONGS_TO, nessun Cluster per -1
    clusters = _read_csv(output_dir / "clusters.csv")
    assert clusters == [{"cluster_id": "5", "label": "Cluster Five"}]
    belongs_to = _read_csv(output_dir / "belongs_to.csv")
    assert {r["mail_id"] for r in belongs_to} == {"mail-1", "mail-3"}
    assert all(r["mail_id"] != "mail-2" for r in belongs_to)

    # Thread/PART_OF sempre presenti, una riga per mail
    threads = _read_csv(output_dir / "threads.csv")
    assert {t["doc_id"] for t in threads} == {"doc-1", "doc-2"}
    part_of = _read_csv(output_dir / "part_of.csv")
    assert len(part_of) == 3
    assert {"mail_id": "mail-1", "doc_id": "doc-1", "position": "0"} in part_of
    assert {"mail_id": "mail-2", "doc_id": "doc-1", "position": "1"} in part_of


def test_build_graph_csvs_sender_parse_failure_skips_only_sent(tmp_path):
    rows = [
        _base_row(id="mail-1", doc_id="doc-1", sender=json.dumps(42)),
    ]
    parquet_path = _write_parquet(tmp_path, rows)
    output_dir = tmp_path / "graph"

    counts = build_graph_csvs(parquet_path=parquet_path, output_dir=output_dir)

    assert counts["mails"] == 1
    assert counts["sent_skipped_parse_failure"] == 1
    mails = _read_csv(output_dir / "mails.csv")
    assert len(mails) == 1
    sent_rows = _read_csv(output_dir / "sent.csv")
    assert sent_rows == []
