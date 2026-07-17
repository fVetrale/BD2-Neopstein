import json

from src.etl.clean_data import (
    extract_domain,
    is_redacted_address,
    normalize_address,
    parse_address_entry,
    parse_recipient_field,
)


def test_parse_address_entry_name_and_address():
    assert parse_address_entry("Jeffrey Epstein <jeffrey@example.com>") == (
        "Jeffrey Epstein",
        "jeffrey@example.com",
    )


def test_parse_address_entry_only_angle_brackets_no_name():
    assert parse_address_entry("<jeffrey@example.com>") == (None, "jeffrey@example.com")


def test_parse_address_entry_bare_address_no_brackets():
    assert parse_address_entry("jeffrey@example.com") == (None, "jeffrey@example.com")


def test_parse_address_entry_inverted_name_captured_as_is():
    name, address = parse_address_entry("Epstein Jeffrey <jeffrey@example.com>")
    assert name == "Epstein Jeffrey"
    assert address == "jeffrey@example.com"


def test_normalize_address():
    assert normalize_address("  Jeffrey@EXAMPLE.com  ") == "jeffrey@example.com"


def test_extract_domain():
    assert extract_domain("jeffrey@example.com") == "example.com"


def test_extract_domain_no_at():
    assert extract_domain("no-at-here") is None


def test_is_redacted_address():
    assert is_redacted_address("redacted-entry") is True
    assert is_redacted_address("jeffrey@example.com") is False


def test_parse_recipient_field_multiple_valid_entries():
    raw = json.dumps(
        [
            "Alice One <alice@example.com>",
            "Bob Two <bob@example.org>",
        ]
    )
    result = parse_recipient_field(raw, "mail-1", "to")
    assert result == [
        {"name": "Alice One", "address": "alice@example.com", "domain": "example.com", "is_redacted": False},
        {"name": "Bob Two", "address": "bob@example.org", "domain": "example.org", "is_redacted": False},
    ]


def test_parse_recipient_field_only_address_entries():
    raw = json.dumps(["carol@example.com", "<dave@example.com>"])
    result = parse_recipient_field(raw, "mail-2", "to")
    assert result == [
        {"name": None, "address": "carol@example.com", "domain": "example.com", "is_redacted": False},
        {"name": None, "address": "dave@example.com", "domain": "example.com", "is_redacted": False},
    ]


def test_parse_recipient_field_inverted_name():
    raw = json.dumps(["Epstein Jeffrey <jeffrey@example.com>"])
    result = parse_recipient_field(raw, "mail-3", "to")
    assert result[0]["name"] == "Epstein Jeffrey"
    assert result[0]["address"] == "jeffrey@example.com"


def test_parse_recipient_field_fully_redacted_entry():
    raw = json.dumps(["REDACTED"])
    result = parse_recipient_field(raw, "mail-4", "to")
    assert result == [
        {"name": None, "address": "redacted:mail-4:to:0", "domain": None, "is_redacted": True}
    ]


def test_parse_recipient_field_empty_variants():
    assert parse_recipient_field(None, "mail-5", "to") == []
    assert parse_recipient_field("", "mail-5", "to") == []
    assert parse_recipient_field("[]", "mail-5", "to") == []


def test_parse_recipient_field_mixed_valid_and_redacted():
    raw = json.dumps(
        [
            "Alice One <alice@example.com>",
            "REDACTED NAME <REDACTED>",
            "bob@example.org",
        ]
    )
    result = parse_recipient_field(raw, "mail-6", "to")
    assert result == [
        {"name": "Alice One", "address": "alice@example.com", "domain": "example.com", "is_redacted": False},
        {"name": "REDACTED NAME", "address": "redacted:mail-6:to:1", "domain": None, "is_redacted": True},
        {"name": None, "address": "bob@example.org", "domain": "example.org", "is_redacted": False},
    ]


def test_parse_recipient_field_same_index_different_field_no_collision():
    raw_to = json.dumps(["REDACTED"])
    raw_cc = json.dumps(["REDACTED"])
    to_result = parse_recipient_field(raw_to, "mail-7", "to")
    cc_result = parse_recipient_field(raw_cc, "mail-7", "cc")
    assert to_result[0]["address"] != cc_result[0]["address"]
