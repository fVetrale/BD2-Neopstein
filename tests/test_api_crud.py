from neo4j.exceptions import ConstraintError

from fastapi.testclient import TestClient

from src.api.deps import get_session
from src.api.main import app


# --- fake session/result (nessun Neo4j reale) --------------------------------
# Stesso pattern di _FakeRecord/_FakeResult/_FakeSession usato in
# tests/test_api_analytics.py, esteso con la capacità di simulare
# `neo4j.exceptions.ConstraintError` sollevata da `run()` (per testare il
# mapping a 409 sui duplicati in create).


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
    def __init__(self, records: list[dict] | None = None, raise_constraint_error: bool = False):
        self.query: str | None = None
        self.params: dict | None = None
        self._records = records or []
        self._raise_constraint_error = raise_constraint_error

    def run(self, query: str, **kwargs):
        self.query = query
        self.params = kwargs
        if self._raise_constraint_error:
            raise ConstraintError("constraint violation")
        return _FakeResult(self._records)


def _use_session(session: _FakeSession) -> None:
    app.dependency_overrides[get_session] = lambda: session


def _clear_override() -> None:
    app.dependency_overrides.pop(get_session, None)


client = TestClient(app)


# --- Mail ---------------------------------------------------------------------


def test_create_mail_ok():
    row = {
        "id": "mail-1",
        "subject": "Ciao",
        "body": "corpo",
        "sent_at": "2020-01-01T00:00:00",
        "redaction_count": 0,
        "redaction_ratio": 0.0,
        "attachment_count": 0,
        "is_promotional": False,
    }
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.post("/mails", json={"id": "mail-1", "subject": "Ciao", "body": "corpo"})
        assert response.status_code == 201
        assert response.json() == row
    finally:
        _clear_override()


def test_create_mail_duplicate_returns_409():
    _use_session(_FakeSession(raise_constraint_error=True))
    try:
        response = client.post("/mails", json={"id": "mail-1"})
        assert response.status_code == 409
        assert "mail-1" in response.json()["detail"]
    finally:
        _clear_override()


def test_update_mail_ok():
    row = {
        "id": "mail-1",
        "subject": "Nuovo",
        "body": None,
        "sent_at": None,
        "redaction_count": None,
        "redaction_ratio": None,
        "attachment_count": None,
        "is_promotional": None,
    }
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.put("/mails/mail-1", json={"subject": "Nuovo"})
        assert response.status_code == 200
        assert response.json() == row
    finally:
        _clear_override()


def test_update_mail_not_found_returns_404():
    _use_session(_FakeSession(records=[]))
    try:
        response = client.put("/mails/mail-inesistente", json={"subject": "Nuovo"})
        assert response.status_code == 404
        assert "mail-inesistente" in response.json()["detail"]
    finally:
        _clear_override()


def test_delete_mail_ok():
    _use_session(_FakeSession(records=[{"deleted": 1}]))
    try:
        response = client.delete("/mails/mail-1")
        assert response.status_code == 204
    finally:
        _clear_override()


def test_delete_mail_not_found_returns_404():
    _use_session(_FakeSession(records=[{"deleted": 0}]))
    try:
        response = client.delete("/mails/mail-inesistente")
        assert response.status_code == 404
        assert "mail-inesistente" in response.json()["detail"]
    finally:
        _clear_override()


def test_create_mail_missing_required_field_returns_422():
    _use_session(_FakeSession())
    try:
        response = client.post("/mails", json={"subject": "Senza id"})
        assert response.status_code == 422
    finally:
        _clear_override()


# --- Person ---------------------------------------------------------------------


def test_create_person_ok():
    row = {"person_id": "p1", "display_name": "Jeffrey Epstein", "is_unknown": False, "is_epstein": True}
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.post(
            "/persons", json={"person_id": "p1", "display_name": "Jeffrey Epstein", "is_epstein": True}
        )
        assert response.status_code == 201
        assert response.json() == row
    finally:
        _clear_override()


def test_create_person_duplicate_returns_409():
    _use_session(_FakeSession(raise_constraint_error=True))
    try:
        response = client.post("/persons", json={"person_id": "p1"})
        assert response.status_code == 409
        assert "p1" in response.json()["detail"]
    finally:
        _clear_override()


def test_get_person_ok():
    row = {"person_id": "p1", "display_name": "Jeffrey Epstein", "is_unknown": False, "is_epstein": True}
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.get("/persons/p1")
        assert response.status_code == 200
        assert response.json() == row
    finally:
        _clear_override()


def test_get_person_not_found_returns_404():
    _use_session(_FakeSession(records=[]))
    try:
        response = client.get("/persons/p-inesistente")
        assert response.status_code == 404
        assert "p-inesistente" in response.json()["detail"]
    finally:
        _clear_override()


def test_update_person_ok():
    row = {"person_id": "p1", "display_name": "Nuovo Nome", "is_unknown": False, "is_epstein": False}
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.put("/persons/p1", json={"display_name": "Nuovo Nome"})
        assert response.status_code == 200
        assert response.json() == row
    finally:
        _clear_override()


def test_update_person_not_found_returns_404():
    _use_session(_FakeSession(records=[]))
    try:
        response = client.put("/persons/p-inesistente", json={"display_name": "Nuovo Nome"})
        assert response.status_code == 404
        assert "p-inesistente" in response.json()["detail"]
    finally:
        _clear_override()


def test_delete_person_ok():
    _use_session(_FakeSession(records=[{"deleted": 1}]))
    try:
        response = client.delete("/persons/p1")
        assert response.status_code == 204
    finally:
        _clear_override()


def test_delete_person_not_found_returns_404():
    _use_session(_FakeSession(records=[{"deleted": 0}]))
    try:
        response = client.delete("/persons/p-inesistente")
        assert response.status_code == 404
        assert "p-inesistente" in response.json()["detail"]
    finally:
        _clear_override()


def test_create_person_missing_required_field_returns_422():
    _use_session(_FakeSession())
    try:
        response = client.post("/persons", json={"display_name": "Senza id"})
        assert response.status_code == 422
    finally:
        _clear_override()


# --- Cluster ---------------------------------------------------------------------


def test_create_cluster_ok():
    row = {"cluster_id": 1, "label": "Finance"}
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.post("/clusters", json={"cluster_id": 1, "label": "Finance"})
        assert response.status_code == 201
        assert response.json() == row
    finally:
        _clear_override()


def test_create_cluster_duplicate_returns_409():
    _use_session(_FakeSession(raise_constraint_error=True))
    try:
        response = client.post("/clusters", json={"cluster_id": 1, "label": "Finance"})
        assert response.status_code == 409
        assert "1" in response.json()["detail"]
    finally:
        _clear_override()


def test_get_cluster_ok():
    row = {"cluster_id": 1, "label": "Finance"}
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.get("/clusters/1")
        assert response.status_code == 200
        assert response.json() == row
    finally:
        _clear_override()


def test_get_cluster_not_found_returns_404():
    _use_session(_FakeSession(records=[]))
    try:
        response = client.get("/clusters/999")
        assert response.status_code == 404
        assert "999" in response.json()["detail"]
    finally:
        _clear_override()


def test_update_cluster_ok():
    row = {"cluster_id": 1, "label": "Nuovo"}
    _use_session(_FakeSession(records=[row]))
    try:
        response = client.put("/clusters/1", json={"label": "Nuovo"})
        assert response.status_code == 200
        assert response.json() == row
    finally:
        _clear_override()


def test_update_cluster_not_found_returns_404():
    _use_session(_FakeSession(records=[]))
    try:
        response = client.put("/clusters/999", json={"label": "Nuovo"})
        assert response.status_code == 404
        assert "999" in response.json()["detail"]
    finally:
        _clear_override()


def test_delete_cluster_ok():
    _use_session(_FakeSession(records=[{"deleted": 1}]))
    try:
        response = client.delete("/clusters/1")
        assert response.status_code == 204
    finally:
        _clear_override()


def test_delete_cluster_not_found_returns_404():
    _use_session(_FakeSession(records=[{"deleted": 0}]))
    try:
        response = client.delete("/clusters/999")
        assert response.status_code == 404
        assert "999" in response.json()["detail"]
    finally:
        _clear_override()


def test_create_cluster_invalid_type_returns_422():
    _use_session(_FakeSession())
    try:
        response = client.post("/clusters", json={"cluster_id": "non-un-int", "label": "Finance"})
        assert response.status_code == 422
    finally:
        _clear_override()


# --- Regressione: ordine di routing /clusters/top-redacted vs /clusters/{cluster_id} ---


def test_top_redacted_still_works_after_cluster_id_route_added():
    rows = [
        {"cluster_id": 1, "label": "Finance", "total_redactions": 42},
        {"cluster_id": 2, "label": "Legal", "total_redactions": 10},
    ]
    _use_session(_FakeSession(records=rows))
    try:
        response = client.get("/clusters/top-redacted")
        assert response.status_code == 200
        assert response.json() == rows
    finally:
        _clear_override()
