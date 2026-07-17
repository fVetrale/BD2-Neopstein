"""Parsing deterministico degli indirizzi email (sender/to/cc/bcc).

Nessuna chiamata LLM: json.loads + regex, come da regole ETL in CLAUDE.md.
"""

from __future__ import annotations

import json
import re

_ADDRESS_RE = re.compile(r"^(.*?)\s*<([^>]+)>$")


def parse_address_entry(raw: str) -> tuple[str | None, str]:
    """Estrae (nome, indirizzo) da una entry tipo 'Nome <indirizzo>' o '<indirizzo>'.

    Se non matcha il pattern con '<...>', l'intera stringa trimmata è l'indirizzo.
    """
    match = _ADDRESS_RE.match(raw)
    if match:
        name = match.group(1).strip()
        address = match.group(2)
        return (name if name else None), address
    return None, raw.strip()


def normalize_address(address: str) -> str:
    return address.strip().lower()


def extract_domain(address: str) -> str | None:
    if "@" not in address:
        return None
    return address.split("@", 1)[1]


def is_redacted_address(address: str) -> bool:
    return "@" not in address


def parse_recipient_field(raw_json: str | None, mail_id: str, field: str) -> list[dict]:
    if not raw_json or raw_json == "[]":
        return []

    try:
        entries = json.loads(raw_json)
    except json.JSONDecodeError:
        entries = [raw_json]

    result = []
    for n, entry in enumerate(entries):
        entry = entry or ""
        name, address = parse_address_entry(entry)
        address = normalize_address(address)

        if is_redacted_address(address):
            result.append(
                {
                    "name": name,
                    "address": f"redacted:{mail_id}:{field}:{n}",
                    "domain": None,
                    "is_redacted": True,
                }
            )
        else:
            result.append(
                {
                    "name": name,
                    "address": address,
                    "domain": extract_domain(address),
                    "is_redacted": False,
                }
            )

    return result
