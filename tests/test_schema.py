from src.schema import CONSTRAINTS, INDEXES, apply_schema


class _FakeSession:
    """Session fittizia che registra le query eseguite, senza un vero DB."""

    def __init__(self):
        self.queries: list[str] = []

    def run(self, statement: str):
        self.queries.append(statement)


def test_apply_schema_runs_all_constraints_and_indexes():
    session = _FakeSession()

    apply_schema(session)

    assert len(session.queries) == len(CONSTRAINTS) + len(INDEXES)


def test_apply_schema_queries_contain_if_not_exists():
    session = _FakeSession()

    apply_schema(session)

    for query in session.queries:
        assert "IF NOT EXISTS" in query


def test_apply_schema_covers_all_node_key_constraints():
    session = _FakeSession()

    apply_schema(session)

    expected = {
        ("Person", "person_id"),
        ("EmailAddress", "address"),
        ("Mail", "id"),
        ("Cluster", "cluster_id"),
        ("Thread", "doc_id"),
    }
    for label, key in expected:
        assert any(
            f"FOR (" in query and f":{label})" in query and f".{key} IS UNIQUE" in query
            for query in session.queries
        ), f"manca il constraint unique per {label}.{key}"


def test_apply_schema_covers_required_indexes():
    session = _FakeSession()

    apply_schema(session)

    expected = {
        ("Mail", "sent_at"),
        ("EmailAddress", "domain"),
    }
    for label, attr in expected:
        assert any(
            f":{label})" in query and f"ON (" in query and f".{attr})" in query
            for query in session.queries
        ), f"manca l'indice per {label}.{attr}"
