from src.etl.entity_resolution import (
    normalize_name,
    resolve_persons,
    surname_initial_keys,
)


def test_normalize_name():
    assert normalize_name("  J.  Epstein  ") == "j epstein"


def test_surname_initial_keys_both_orderings_match():
    keys_first_last = surname_initial_keys(normalize_name("Jeffrey Epstein"))
    keys_last_first = surname_initial_keys(normalize_name("Epstein Jeffrey"))
    assert keys_first_last & keys_last_first


def test_exact_normalized_name_match_one_person():
    mentions = [
        ("Jeffrey Epstein", "jeffrey@example.com"),
        ("jeffrey  epstein", "jeffrey@example.com"),
    ]
    result = resolve_persons(mentions)
    assert len(result.persons) == 1
    assert result.raw_name_to_person_id["Jeffrey Epstein"] == result.raw_name_to_person_id["jeffrey  epstein"]


def test_inverted_order_surname_initial_merge():
    mentions = [
        ("Jeffrey Epstein", "jeffrey@example.com"),
        ("Epstein Jeffrey", "jeffrey2@example.com"),
    ]
    result = resolve_persons(mentions)
    assert len(result.persons) == 1
    assert result.raw_name_to_person_id["Jeffrey Epstein"] == result.raw_name_to_person_id["Epstein Jeffrey"]


def test_shared_address_merge():
    mentions = [
        ("Jeffrey Epstein", "shared@example.com"),
        ("J.E.", "shared@example.com"),
    ]
    result = resolve_persons(mentions)
    assert len(result.persons) == 1


def test_none_name_excluded_from_resolution():
    mentions = [(None, "alice@example.com")]
    result = resolve_persons(mentions)
    assert result.persons == []
    assert result.raw_name_to_person_id == {}


def test_is_epstein_flag_from_sender_addresses():
    mentions = [("Jeffrey Epstein", "jeffrey@example.com")]
    result = resolve_persons(
        mentions,
        epstein_sender_addresses={"jeffrey@example.com"},
    )
    assert result.persons[0].is_epstein is True
