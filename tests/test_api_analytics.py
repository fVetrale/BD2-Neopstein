from fastapi.testclient import TestClient

from src.api.deps import get_session
from src.api.main import app


# --- fake session/result (nessun Neo4j reale) --------------------------------
# Stesso pattern di _FakeSession/_FakeResult/_FakeRecord usato in
# tests/test_query_cluster.py e tests/test_query_mail.py: `run()` registra
# query/parametri e ritorna sempre gli stessi record preconfigurati, dato che
# ogni endpoint testato esegue una singola query per request.


class _FakeRecord(dict):
    def data(self) -> dict:
        return dict(self)


class _FakeResult:
    def __init__(self, records: list[dict]):
        self._records = [_FakeRecord(r) for r in records]

    def __iter__(self):
        return iter(self._records)

    def single(self):
        return self._records[0] if self._records else None


class _FakeSession:
    def __init__(self, records: list[dict] | None = None):
        self.query: str | None = None
        self.params: dict | None = None
        self._records = records or []

    def run(self, query: str, **kwargs):
        self.query = query
        self.params = kwargs
        return _FakeResult(self._records)


def _use_session(session: _FakeSession) -> None:
    app.dependency_overrides[get_session] = lambda: session


def _clear_override() -> None:
    app.dependency_overrides.pop(get_session, None)


client = TestClient(app)


# --- GET /clusters/{cluster_id}/mails ----------------------------------------


def test_cluster_mails_ok():
    rows = [
        {"id": "m1", "subject": "Hello", "sent_at": "2020-01-01T00:00:00", "redaction_count": 2, "probability": 0.9},
        {"id": "m2", "subject": "World", "sent_at": "2020-01-02T00:00:00", "redaction_count": 0, "probability": 0.5},
    ]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/clusters/3/mails")
        assert response.status_code == 200
        assert response.json() == rows
    finally:
        _clear_override()


def test_cluster_mails_pagination_slices_result():
    rows = [
        {"id": "m1", "subject": "A", "sent_at": None, "redaction_count": 0, "probability": None},
        {"id": "m2", "subject": "B", "sent_at": None, "redaction_count": 0, "probability": None},
        {"id": "m3", "subject": "C", "sent_at": None, "redaction_count": 0, "probability": None},
    ]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/clusters/3/mails", params={"limit": 1, "offset": 1})
        assert response.status_code == 200
        assert response.json() == [rows[1]]
    finally:
        _clear_override()


# --- GET /clusters/{cluster_id}/persons --------------------------------------


def test_cluster_persons_ok():
    rows = [
        {"person_id": "p1", "display_name": "Jeffrey Epstein", "is_unknown": False, "is_epstein": True},
    ]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/clusters/3/persons")
        assert response.status_code == 200
        assert response.json() == rows
    finally:
        _clear_override()


# --- GET /clusters/top-redacted -----------------------------------------------


def test_top_redacted_clusters_ok_and_reconciles_limit_semantics():
    rows = [
        {"cluster_id": 1, "label": "Finance", "total_redactions": 42},
        {"cluster_id": 2, "label": "Legal", "total_redactions": 10},
        {"cluster_id": 3, "label": "Travel", "total_redactions": 5},
    ]
    session = _FakeSession(records=rows)
    _use_session(session)
    try:
        response = client.get("/clusters/top-redacted", params={"limit": 1, "offset": 1})
        assert response.status_code == 200
        # limit/offset della issue: offset=1, limit=1 -> il secondo elemento
        assert response.json() == [rows[1]]
        # limit "top N" sottostante riconciliato con offset+limit richiesti
        assert session.params == {"limit": 2}
    finally:
        _clear_override()


def test_top_redacted_clusters_default_pagination():
    rows = [{"cluster_id": 1, "label": "Finance", "total_redactions": 42}]
    session = _FakeSession(records=rows)
    _use_session(session)
    try:
        response = client.get("/clusters/top-redacted")
        assert response.status_code == 200
        assert response.json() == rows
        assert session.params == {"limit": 50}
    finally:
        _clear_override()


# --- GET /persons/{person_id}/mails ------------------------------------------


def test_person_mails_ok():
    rows = [{"id": "m1", "subject": "Hi", "sent_at": "2020-01-01T00:00:00"}]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/persons/p1/mails")
        assert response.status_code == 200
        assert response.json() == rows
    finally:
        _clear_override()


# --- GET /persons/{person_id}/connected --------------------------------------


def test_person_connected_ok():
    rows = [{"person_id": "p2", "display_name": "Bob"}]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/persons/p1/connected")
        assert response.status_code == 200
        assert response.json() == rows
    finally:
        _clear_override()


# --- GET /persons/{person_id}/addresses --------------------------------------


def test_person_addresses_ok():
    rows = [{"address": "a@example.com", "domain": "example.com", "is_redacted": False}]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/persons/p1/addresses")
        assert response.status_code == 200
        assert response.json() == rows
    finally:
        _clear_override()


def test_person_addresses_pagination_offset_beyond_range_returns_empty():
    rows = [{"address": "a@example.com", "domain": "example.com", "is_redacted": False}]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/persons/p1/addresses", params={"limit": 50, "offset": 5})
        assert response.status_code == 200
        assert response.json() == []
    finally:
        _clear_override()


# --- GET /mails/{mail_id} -----------------------------------------------------


def test_mail_info_ok():
    row = {
        "id": "mail-1",
        "subject": "Ciao",
        "sent_at": "2020-01-01T00:00:00",
        "redaction_count": 2,
        "redaction_ratio": 0.1,
        "attachment_count": 1,
        "is_promotional": False,
        "cluster_id": 3,
        "label": "Meeting",
        "probability": 0.9,
    }
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.get("/mails/mail-1")
        assert response.status_code == 200
        assert response.json() == row
    finally:
        _clear_override()


def test_mail_info_without_cluster_fields_are_null():
    row = {
        "id": "mail-2",
        "subject": "Senza cluster",
        "sent_at": "2020-02-02T00:00:00",
        "redaction_count": 0,
        "redaction_ratio": 0.0,
        "attachment_count": 0,
        "is_promotional": True,
        "cluster_id": None,
        "label": None,
        "probability": None,
    }
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.get("/mails/mail-2")
        assert response.status_code == 200
        body = response.json()
        assert body["cluster_id"] is None
        assert body["label"] is None
        assert body["probability"] is None
    finally:
        _clear_override()


def test_mail_info_not_found_returns_404():
    _use_session(_FakeSession(records=[]))
    try:
        response = client.get("/mails/mail-inesistente")
        assert response.status_code == 404
        assert "mail-inesistente" in response.json()["detail"]
    finally:
        _clear_override()


# --- GET /mails/{mail_id}/persons --------------------------------------------


def test_mail_persons_ok():
    rows = [
        {
            "person_id": "p1",
            "display_name": "Jeffrey Epstein",
            "is_unknown": False,
            "is_epstein": True,
            "roles": ["sender"],
        },
        {
            "person_id": "p2",
            "display_name": "Ghislaine Maxwell",
            "is_unknown": False,
            "is_epstein": False,
            "roles": ["cc", "to"],
        },
    ]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/mails/mail-1/persons")
        assert response.status_code == 200
        assert response.json() == rows
    finally:
        _clear_override()


def test_mail_persons_pagination_slices_result():
    rows = [
        {"person_id": "p1", "display_name": "A", "is_unknown": False, "is_epstein": False, "roles": ["sender"]},
        {"person_id": "p2", "display_name": "B", "is_unknown": False, "is_epstein": False, "roles": ["to"]},
    ]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/mails/mail-1/persons", params={"limit": 1, "offset": 0})
        assert response.status_code == 200
        assert response.json() == [rows[0]]
    finally:
        _clear_override()
