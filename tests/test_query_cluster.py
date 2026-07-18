from src.queries import cluster


# --- fake session/result (nessun Neo4j reale) --------------------------------


class _FakeRecord(dict):
    """Dict-like che imita `neo4j.Record`: supporta `.data()` e accesso a chiave."""

    def data(self) -> dict:
        return dict(self)


class _FakeResult:
    """Risultato fittizio: iterabile sui record e con `.single()`."""

    def __init__(self, records: list[dict]):
        self._records = [_FakeRecord(r) for r in records]

    def __iter__(self):
        return iter(self._records)

    def single(self):
        return self._records[0] if self._records else None


class _FakeSession:
    """Session fittizia che registra la query e i parametri eseguiti."""

    def __init__(self, records: list[dict] | None = None):
        self.query: str | None = None
        self.params: dict | None = None
        self._records = records or []

    def run(self, query: str, **kwargs):
        self.query = query
        self.params = kwargs
        return _FakeResult(self._records)


# --- get_cluster_mails --------------------------------------------------------


def test_get_cluster_mails_query_and_params():
    session = _FakeSession(records=[])

    cluster.get_cluster_mails(session, cluster_id=3)

    assert "BELONGS_TO" in session.query
    assert "Mail" in session.query
    assert "Cluster" in session.query
    assert session.params == {"cluster_id": 3}


def test_get_cluster_mails_builds_rows_from_records():
    rows = [
        {"id": "m1", "subject": "Hello", "sent_at": "2020-01-01T00:00:00", "redaction_count": 2, "probability": 0.9},
        {"id": "m2", "subject": "World", "sent_at": "2020-01-02T00:00:00", "redaction_count": 0, "probability": 0.5},
    ]
    session = _FakeSession(records=rows)

    result = cluster.get_cluster_mails(session, cluster_id=3)

    assert result == rows


def test_get_cluster_mails_empty_when_no_mails():
    session = _FakeSession(records=[])

    result = cluster.get_cluster_mails(session, cluster_id=999)

    assert result == []


# --- get_cluster_persons -------------------------------------------------------


def test_get_cluster_persons_query_and_params():
    session = _FakeSession(records=[])

    cluster.get_cluster_persons(session, cluster_id=3)

    assert "BELONGS_TO" in session.query
    assert "OWNS" in session.query
    assert "SENT" in session.query
    assert "TO|CC|BCC" in session.query
    assert "DISTINCT" in session.query
    assert session.params == {"cluster_id": 3}


def test_get_cluster_persons_builds_rows_from_records():
    rows = [
        {"person_id": "p1", "display_name": "Jeffrey Epstein", "is_unknown": False, "is_epstein": True},
        {"person_id": "p2", "display_name": "Jane Doe", "is_unknown": False, "is_epstein": False},
    ]
    session = _FakeSession(records=rows)

    result = cluster.get_cluster_persons(session, cluster_id=3)

    assert result == rows


def test_get_cluster_persons_empty_when_no_person_owns_email():
    session = _FakeSession(records=[])

    result = cluster.get_cluster_persons(session, cluster_id=3)

    assert result == []


# --- get_top_redacted_clusters -------------------------------------------------


def test_get_top_redacted_clusters_query_and_params():
    session = _FakeSession(records=[])

    cluster.get_top_redacted_clusters(session, limit=5)

    assert "BELONGS_TO" in session.query
    assert "sum(" in session.query
    assert "coalesce(" in session.query
    assert "ORDER BY" in session.query
    assert "DESC" in session.query
    assert "LIMIT" in session.query
    assert session.params == {"limit": 5}


def test_get_top_redacted_clusters_default_limit():
    session = _FakeSession(records=[])

    cluster.get_top_redacted_clusters(session)

    assert session.params == {"limit": 10}


def test_get_top_redacted_clusters_builds_rows_from_records():
    rows = [
        {"cluster_id": 1, "label": "Finance", "total_redactions": 42},
        {"cluster_id": 2, "label": "Legal", "total_redactions": 10},
    ]
    session = _FakeSession(records=rows)

    result = cluster.get_top_redacted_clusters(session, limit=2)

    assert result == rows
