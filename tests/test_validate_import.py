from src.etl import validate_import


# --- fake driver/session (no Neo4j reale) ------------------------------------


class _FakeSession:
    """Session fittizia che ritorna, per ogni `run`, il prossimo valore da una coda."""

    def __init__(self, run_results):
        self._run_results = list(run_results)

    def run(self, query: str, **kwargs):
        value = self._run_results.pop(0)
        return _FakeResult(value)

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
    def __init__(self, run_results):
        self._run_results = run_results

    def session(self):
        return _FakeSession(self._run_results)


# --- check_graph_integrity -----------------------------------------------------


def test_check_graph_integrity_returns_expected_structure_and_percentages():
    # ordine delle query in _INTEGRITY_QUERIES: mail_total, mail_without_sent,
    # mail_without_belongs_to, email_address_total, email_address_without_owns
    run_results = [10, 3, 4, 20, 15]
    driver = _FakeDriver(run_results)

    results = validate_import.check_graph_integrity(driver)

    assert results["mail"]["total"] == 10
    assert results["mail"]["without_sent"] == 3
    assert results["mail"]["without_sent_pct"] == 30.0
    assert results["mail"]["without_belongs_to"] == 4
    assert results["mail"]["without_belongs_to_pct"] == 40.0

    assert results["email_address"]["total"] == 20
    assert results["email_address"]["without_owns"] == 15
    assert results["email_address"]["without_owns_pct"] == 75.0


def test_check_graph_integrity_handles_division_by_zero():
    run_results = [0, 0, 0, 0, 0]
    driver = _FakeDriver(run_results)

    results = validate_import.check_graph_integrity(driver)

    assert results["mail"]["total"] == 0
    assert results["mail"]["without_sent_pct"] == 0.0
    assert results["mail"]["without_belongs_to_pct"] == 0.0
    assert results["email_address"]["total"] == 0
    assert results["email_address"]["without_owns_pct"] == 0.0


def test_pct_helper_division_by_zero():
    assert validate_import._pct(5, 0) == 0.0
    assert validate_import._pct(0, 0) == 0.0


# --- format_integrity_report ----------------------------------------------------


def test_format_integrity_report_contains_key_numbers():
    run_results = [400000, 41021, 218107, 695787, 676324]
    driver = _FakeDriver(run_results)
    results = validate_import.check_graph_integrity(driver)

    report = validate_import.format_integrity_report(results)

    assert isinstance(report, str)
    assert report != ""
    assert "400000" in report
    assert "41021" in report
    assert "218107" in report
    assert "695787" in report
    assert "676324" in report
