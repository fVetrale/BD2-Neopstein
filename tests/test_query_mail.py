from src.queries.mail import get_mail_info, get_mail_persons


class _FakeResult:
    """Result fittizio che simula `neo4j.Result`: `.single()` e iterabile."""

    def __init__(self, records: list[dict]):
        self._records = records

    def single(self):
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)


class _FakeSession:
    """Session fittizia: restituisce un `_FakeResult` predefinito per query."""

    def __init__(self, records: list[dict]):
        self._records = records
        self.queries: list[tuple[str, dict]] = []

    def run(self, statement: str, **params):
        self.queries.append((statement, params))
        return _FakeResult(self._records)


def test_get_mail_info_with_cluster():
    session = _FakeSession(
        [
            {
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
        ]
    )

    result = get_mail_info(session, "mail-1")

    assert result == {
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


def test_get_mail_info_without_cluster():
    session = _FakeSession(
        [
            {
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
        ]
    )

    result = get_mail_info(session, "mail-2")

    assert result["cluster_id"] is None
    assert result["label"] is None
    assert result["probability"] is None
    assert result["id"] == "mail-2"
    assert result["subject"] == "Senza cluster"
    assert result["is_promotional"] is True


def test_get_mail_info_mail_not_found():
    session = _FakeSession([])

    result = get_mail_info(session, "mail-inesistente")

    assert result is None


def test_get_mail_persons_multiple_roles():
    session = _FakeSession(
        [
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
                "roles": ["to", "cc"],
            },
            {
                "person_id": "p3",
                "display_name": "Unknown",
                "is_unknown": True,
                "is_epstein": False,
                "roles": ["bcc"],
            },
        ]
    )

    result = get_mail_persons(session, "mail-1")

    assert result == [
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
        {
            "person_id": "p3",
            "display_name": "Unknown",
            "is_unknown": True,
            "is_epstein": False,
            "roles": ["bcc"],
        },
    ]


def test_get_mail_persons_mail_not_found():
    session = _FakeSession([])

    result = get_mail_persons(session, "mail-inesistente")

    assert result == []


def test_get_mail_persons_deduplicates_same_person():
    # Simula una Person collegata alla mail tramite più indirizzi/ruoli:
    # la query Cypher aggrega già i ruoli lato server (collect DISTINCT),
    # quindi il fake session restituisce una sola riga con roles multipli.
    session = _FakeSession(
        [
            {
                "person_id": "p1",
                "display_name": "Jeffrey Epstein",
                "is_unknown": False,
                "is_epstein": True,
                "roles": ["sender", "to"],
            }
        ]
    )

    result = get_mail_persons(session, "mail-1")

    assert len(result) == 1
    assert result[0]["person_id"] == "p1"
    assert result[0]["roles"] == ["sender", "to"]
