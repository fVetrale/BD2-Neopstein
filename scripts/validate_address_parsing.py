"""Validazione ad-hoc del parsing indirizzi su dato reale (parquet).

Legge il parquet reale, applica parse_recipient_field alle colonne
sender/to_recipients/cc_recipients/bcc_recipients su tutte le righe.

IMPORTANTE (regola privacy dati): stampa SOLO conteggi aggregati.
Nessun nome, indirizzo o testo reale viene mai stampato/loggato.
"""

import sys
from pathlib import Path

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.etl.clean_data import parse_recipient_field  # noqa: E402

PARQUET_PATH = "data/raw/jmail_emails_clustered_sample_thread_aware.parquet"
COLUMNS = ["id", "sender", "to_recipients", "cc_recipients", "bcc_recipients"]


def main() -> None:
    table = pq.read_table(PARQUET_PATH, columns=COLUMNS)
    ids = table.column("id").to_pylist()

    field_columns = ["sender", "to_recipients", "cc_recipients", "bcc_recipients"]
    field_names = {
        "sender": "sender",
        "to_recipients": "to",
        "cc_recipients": "cc",
        "bcc_recipients": "bcc",
    }

    total_rows = len(ids)
    total_entries = 0
    redacted_entries = 0
    errors = 0

    for field in field_columns:
        raw_values = table.column(field).to_pylist()
        for mail_id, raw in zip(ids, raw_values):
            try:
                entries = parse_recipient_field(raw, mail_id, field_names[field])
            except Exception:
                errors += 1
                continue
            total_entries += len(entries)
            redacted_entries += sum(1 for e in entries if e["is_redacted"])

    redacted_pct = (redacted_entries / total_entries * 100) if total_entries else 0.0

    print(f"righe totali processate: {total_rows}")
    print(f"campi processati per riga: {len(field_columns)} (sender, to, cc, bcc)")
    print(f"entry totali parsate: {total_entries}")
    print(f"entry redacted: {redacted_entries} ({redacted_pct:.2f}%)")
    print(f"eccezioni durante il parsing: {errors}")


if __name__ == "__main__":
    main()
