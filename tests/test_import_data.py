import csv
from pathlib import Path

from src.etl import import_data


# --- fake driver/session (no Neo4j reale) ------------------------------------


class _FakeSession:
    """Session fittizia che registra le query e i parametri eseguiti."""

    def __init__(self, run_results=None):
        self.calls: list[tuple[str, dict]] = []
        # coda di risultati per session.run(...).single()["c"], usata solo
        # dai test su verify_counts.
        self._run_results = list(run_results) if run_results is not None else None

    def run(self, query: str, **kwargs):
        rows = kwargs.get("rows")
        self.calls.append((query, rows))
        if self._run_results is not None:
            value = self._run_results.pop(0)
            return _FakeResult(value)
        return _FakeResult(None)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def single(self):
        return {"c": self._value}


class _FakeDriver:
    """Driver fittizio: ogni `session()` ritorna una nuova _FakeSession che
    condivide la stessa lista di calls (per ispezionare tutte le query
    eseguite durante un intero `run_import`)."""

    def __init__(self, run_results=None):
        self.all_calls: list[tuple[str, dict]] = []
        self._run_results = run_results

    def session(self):
        session = _FakeSession(run_results=self._run_results)
        session.calls = self.all_calls  # condivide la lista con il driver
        return session


# --- helper per scrivere CSV di fixture --------------------------------------


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _make_fixture_csv_dir(tmp_path: Path) -> Path:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()

    _write_csv(
        csv_dir / "persons.csv",
        ["person_id", "display_name", "is_unknown", "is_epstein"],
        [
            {"person_id": "p1", "display_name": "Jeffrey Epstein", "is_unknown": "False", "is_epstein": "True"},
            {"person_id": "p2", "display_name": "Jane Doe", "is_unknown": "False", "is_epstein": "False"},
        ],
    )
    _write_csv(
        csv_dir / "email_addresses.csv",
        ["address", "domain", "is_redacted"],
        [
            {"address": "jeff@example.com", "domain": "example.com", "is_redacted": "False"},
            {"address": "jane@example.com", "domain": "example.com", "is_redacted": "False"},
        ],
    )
    _write_csv(
        csv_dir / "mails.csv",
        ["id", "subject", "body", "sent_at", "redaction_count", "redaction_ratio", "attachment_count", "is_promotional"],
        [
            {
                "id": "m1",
                "subject": "Hello",
                "body": "Body text",
                "sent_at": "2020-01-01T00:00:00",
                "redaction_count": "0",
                "redaction_ratio": "0.0",
                "attachment_count": "1",
                "is_promotional": "False",
            }
        ],
    )
    _write_csv(csv_dir / "clusters.csv", ["cluster_id", "label"], [{"cluster_id": "3", "label": "Finance"}])
    _write_csv(csv_dir / "threads.csv", ["doc_id"], [{"doc_id": "t1"}])
    _write_csv(csv_dir / "owns.csv", ["person_id", "address"], [{"person_id": "p1", "address": "jeff@example.com"}])
    _write_csv(csv_dir / "sent.csv", ["address", "mail_id"], [{"address": "jeff@example.com", "mail_id": "m1"}])
    _write_csv(csv_dir / "to.csv", ["mail_id", "address"], [{"mail_id": "m1", "address": "jane@example.com"}])
    _write_csv(csv_dir / "cc.csv", ["mail_id", "address"], [{"mail_id": "m1", "address": "jane@example.com"}])
    _write_csv(csv_dir / "bcc.csv", ["mail_id", "address"], [{"mail_id": "m1", "address": "jane@example.com"}])
    _write_csv(
        csv_dir / "belongs_to.csv",
        ["mail_id", "cluster_id", "probability"],
        [{"mail_id": "m1", "cluster_id": "3", "probability": "0.87"}],
    )
    _write_csv(
        csv_dir / "part_of.csv",
        ["mail_id", "doc_id", "position"],
        [{"mail_id": "m1", "doc_id": "t1", "position": "0"}],
    )
    return csv_dir


# --- coercizione tipi ---------------------------------------------------------


def test_to_bool():
    assert import_data._to_bool("True") is True
    assert import_data._to_bool("False") is False


def test_to_int_and_to_float():
    assert import_data._to_int("42") == 42
    assert isinstance(import_data._to_int("42"), int)
    assert import_data._to_float("0.5") == 0.5
    assert isinstance(import_data._to_float("0.5"), float)


# --- MERGE, mai CREATE puro ---------------------------------------------------


def _all_import_functions():
    return [
        ("Person", import_data.import_persons),
        ("EmailAddress", import_data.import_email_addresses),
        ("Mail", import_data.import_mails),
        ("Cluster", import_data.import_clusters),
        ("Thread", import_data.import_threads),
        ("OWNS", import_data.import_owns),
        ("SENT", import_data.import_sent),
        ("TO", import_data.import_to),
        ("CC", import_data.import_cc),
        ("BCC", import_data.import_bcc),
        ("BELONGS_TO", import_data.import_belongs_to),
        ("PART_OF", import_data.import_part_of),
    ]


def test_every_import_uses_merge_not_create(tmp_path):
    csv_dir = _make_fixture_csv_dir(tmp_path)

    for label, import_fn in _all_import_functions():
        driver = _FakeDriver()
        import_fn(driver, csv_dir=csv_dir, batch_size=100)

        assert driver.all_calls, f"nessuna query eseguita per {label}"
        for query, _rows in driver.all_calls:
            assert "MERGE" in query, f"manca MERGE nella query per {label}"
            assert "CREATE " not in query, f"CREATE puro non consentito per {label}"


# --- batching ------------------------------------------------------------------


def test_batching_splits_rows_into_multiple_calls(tmp_path):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _write_csv(
        csv_dir / "persons.csv",
        ["person_id", "display_name", "is_unknown", "is_epstein"],
        [
            {"person_id": f"p{i}", "display_name": f"Person {i}", "is_unknown": "False", "is_epstein": "False"}
            for i in range(5)
        ],
    )

    driver = _FakeDriver()
    processed = import_data.import_persons(driver, csv_dir=csv_dir, batch_size=2)

    assert processed == 5
    assert len(driver.all_calls) == 3  # 2 + 2 + 1
    batch_sizes = [len(rows) for _, rows in driver.all_calls]
    assert batch_sizes == [2, 2, 1]


# --- conversione tipi nei parametri passati a session.run ---------------------


def test_types_are_coerced_in_row_params(tmp_path):
    csv_dir = _make_fixture_csv_dir(tmp_path)

    driver = _FakeDriver()
    import_data.import_mails(driver, csv_dir=csv_dir, batch_size=100)

    _query, rows = driver.all_calls[0]
    row = rows[0]
    assert isinstance(row["redaction_count"], int)
    assert isinstance(row["redaction_ratio"], float)
    assert isinstance(row["attachment_count"], int)
    assert isinstance(row["is_promotional"], bool)
    assert row["is_promotional"] is False

    driver2 = _FakeDriver()
    import_data.import_belongs_to(driver2, csv_dir=csv_dir, batch_size=100)
    _query2, rows2 = driver2.all_calls[0]
    row2 = rows2[0]
    assert isinstance(row2["cluster_id"], int)
    assert isinstance(row2["probability"], float)


# --- ordine di run_import: nodi prima delle relazioni --------------------------


def test_run_import_calls_nodes_before_relationships(tmp_path, monkeypatch):
    csv_dir = _make_fixture_csv_dir(tmp_path)
    call_order: list[str] = []

    def _make_tracker(name):
        def _tracked(driver, csv_dir=None, batch_size=None):
            call_order.append(name)
            return 1

        return _tracked

    for key, _ in import_data._NODE_IMPORTS + import_data._RELATIONSHIP_IMPORTS:
        pass  # solo per leggibilità: monkeypatch applicato sotto

    monkeypatch.setattr(import_data, "import_persons", _make_tracker("persons"))
    monkeypatch.setattr(import_data, "import_email_addresses", _make_tracker("email_addresses"))
    monkeypatch.setattr(import_data, "import_mails", _make_tracker("mails"))
    monkeypatch.setattr(import_data, "import_clusters", _make_tracker("clusters"))
    monkeypatch.setattr(import_data, "import_threads", _make_tracker("threads"))
    monkeypatch.setattr(import_data, "import_owns", _make_tracker("owns"))
    monkeypatch.setattr(import_data, "import_sent", _make_tracker("sent"))
    monkeypatch.setattr(import_data, "import_to", _make_tracker("to"))
    monkeypatch.setattr(import_data, "import_cc", _make_tracker("cc"))
    monkeypatch.setattr(import_data, "import_bcc", _make_tracker("bcc"))
    monkeypatch.setattr(import_data, "import_belongs_to", _make_tracker("belongs_to"))
    monkeypatch.setattr(import_data, "import_part_of", _make_tracker("part_of"))
    monkeypatch.setattr(
        import_data,
        "_NODE_IMPORTS",
        [
            ("persons", import_data.import_persons),
            ("email_addresses", import_data.import_email_addresses),
            ("mails", import_data.import_mails),
            ("clusters", import_data.import_clusters),
            ("threads", import_data.import_threads),
        ],
    )
    monkeypatch.setattr(
        import_data,
        "_RELATIONSHIP_IMPORTS",
        [
            ("owns", import_data.import_owns),
            ("sent", import_data.import_sent),
            ("to", import_data.import_to),
            ("cc", import_data.import_cc),
            ("bcc", import_data.import_bcc),
            ("belongs_to", import_data.import_belongs_to),
            ("part_of", import_data.import_part_of),
        ],
    )

    driver = _FakeDriver()
    import_data.run_import(driver, csv_dir=csv_dir, batch_size=100)

    node_names = {"persons", "email_addresses", "mails", "clusters", "threads"}
    rel_names = {"owns", "sent", "to", "cc", "bcc", "belongs_to", "part_of"}
    last_node_index = max(call_order.index(n) for n in node_names)
    first_rel_index = min(call_order.index(n) for n in rel_names)
    assert last_node_index < first_rel_index, f"ordine non rispettato: {call_order}"


# --- expected_counts_from_csv ---------------------------------------------------


def test_expected_counts_from_csv(tmp_path):
    csv_dir = _make_fixture_csv_dir(tmp_path)

    expected = import_data.expected_counts_from_csv(csv_dir)

    assert expected["persons"] == 2
    assert expected["email_addresses"] == 2
    assert expected["mails"] == 1
    assert expected["clusters"] == 1
    assert expected["threads"] == 1
    assert expected["owns"] == 1
    assert expected["sent"] == 1
    assert expected["to"] == 1
    assert expected["cc"] == 1
    assert expected["bcc"] == 1
    assert expected["belongs_to"] == 1
    assert expected["part_of"] == 1


def test_expected_counts_from_csv_dedupes_relations_without_properties(tmp_path):
    csv_dir = _make_fixture_csv_dir(tmp_path)

    # Introduce righe duplicate esatte in to.csv (relazione senza property):
    # il conteggio atteso deve contare le coppie distinte, non le righe grezze.
    _write_csv(
        csv_dir / "to.csv",
        ["mail_id", "address"],
        [
            {"mail_id": "m1", "address": "jane@example.com"},
            {"mail_id": "m1", "address": "jane@example.com"},
            {"mail_id": "m1", "address": "jane@example.com"},
        ],
    )

    expected = import_data.expected_counts_from_csv(csv_dir)

    # to.csv ha 3 righe grezze ma una sola coppia (mail_id, address) distinta.
    assert expected["to"] == 1
    # una chiave di nodo senza duplicati nel fixture resta il conteggio grezzo.
    assert expected["persons"] == 2
    # una relazione CON property (belongs_to) senza duplicati nel fixture
    # resta anch'essa il conteggio grezzo delle righe.
    assert expected["belongs_to"] == 1


# --- verify_counts: match e mismatch --------------------------------------------


def test_verify_counts_all_match(tmp_path):
    csv_dir = _make_fixture_csv_dir(tmp_path)
    expected = import_data.expected_counts_from_csv(csv_dir)
    # una entry per ciascuna chiave in _COUNT_QUERY_BY_KEY, stesso ordine del dict
    run_results = [expected[key] for key in import_data._COUNT_QUERY_BY_KEY]

    driver = _FakeDriver(run_results=run_results)
    results = import_data.verify_counts(driver, csv_dir=csv_dir)

    assert all(v["match"] for v in results.values())
    assert results["persons"]["expected"] == 2
    assert results["persons"]["actual"] == 2


def test_verify_counts_detects_mismatch(tmp_path):
    csv_dir = _make_fixture_csv_dir(tmp_path)
    expected = import_data.expected_counts_from_csv(csv_dir)
    keys = list(import_data._COUNT_QUERY_BY_KEY)
    run_results = [expected[key] for key in keys]
    # forza un mismatch sulla prima chiave
    run_results[0] = expected[keys[0]] + 1

    driver = _FakeDriver(run_results=run_results)
    results = import_data.verify_counts(driver, csv_dir=csv_dir)

    assert results[keys[0]]["match"] is False
    assert results[keys[0]]["actual"] == expected[keys[0]] + 1
    for key in keys[1:]:
        assert results[key]["match"] is True
