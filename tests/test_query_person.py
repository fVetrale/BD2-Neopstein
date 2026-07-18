from src.queries import person


# --- fake session (no Neo4j reale) -------------------------------------------
#
# La fake session NON esegue Cypher: `run(query, **params)` registra la query
# e i parametri, e ritorna direttamente i record fittizi forniti al costruttore.
# Questo significa che eventuali garanzie di deduplica basate su `DISTINCT`
# (che nel DB reale vengono applicate dal motore Cypher) NON possono essere
# osservate "in azione" tramite la fake session: vanno verificate leggendo la
# stringa della query eseguita (assert "DISTINCT ..." in query).


class _FakeSession:
    """Session fittizia che registra le query/parametri eseguiti."""

    def __init__(self, records=None):
        self.calls: list[tuple[str, dict]] = []
        self._records = list(records) if records is not None else []

    def run(self, query: str, **params):
        self.calls.append((query, params))
        return list(self._records)


# --- get_person_mails ----------------------------------------------------------


def test_get_person_mails_query_references_correct_labels_and_relationships():
    session = _FakeSession(records=[])

    person.get_person_mails(session, "p1")

    assert len(session.calls) == 1
    query, params = session.calls[0]
    assert "Person" in query
    assert "EmailAddress" in query
    assert "Mail" in query
    assert "OWNS" in query
    assert "SENT" in query
    assert "TO" in query
    assert "CC" in query
    assert "BCC" in query
    assert params == {"person_id": "p1"}


def test_get_person_mails_query_dedups_via_distinct_on_mail_id():
    # Dedup lato Cypher: verifichiamo che la query contenga DISTINCT sulla
    # chiave logica m.id in entrambi i blocchi UNION, non solo un DISTINCT
    # generico sulle righe del pattern match.
    session = _FakeSession(records=[])

    person.get_person_mails(session, "p1")

    query, _params = session.calls[0]
    assert query.count("DISTINCT m.id") == 2


def test_get_person_mails_parses_records_into_dicts_sorted_by_id():
    records = [
        {"id": "m2", "subject": "Second", "sent_at": "2020-02-01T00:00:00"},
        {"id": "m1", "subject": "First", "sent_at": "2020-01-01T00:00:00"},
    ]
    session = _FakeSession(records=records)

    result = person.get_person_mails(session, "p1")

    assert result == [
        {"id": "m1", "subject": "First", "sent_at": "2020-01-01T00:00:00"},
        {"id": "m2", "subject": "Second", "sent_at": "2020-02-01T00:00:00"},
    ]


def test_get_person_mails_with_duplicate_ids_from_fake_session():
    # La fake session non esegue Cypher reale: se il DB restituisse righe
    # duplicate per via di join su più indirizzi, la deduplica reale avviene
    # nel motore Cypher grazie a `DISTINCT m.id` (verificato nel test sopra).
    # Qui dimostriamo solo che la funzione Python-side NON introduce duplicati
    # aggiuntivi né li rimuove: si limita a trasformare/ordinare ciò che
    # riceve, quindi con record duplicati in ingresso (simulando l'assenza di
    # DISTINCT) il risultato riflette fedelmente l'input.
    records = [
        {"id": "m1", "subject": "First", "sent_at": "2020-01-01T00:00:00"},
        {"id": "m1", "subject": "First", "sent_at": "2020-01-01T00:00:00"},
    ]
    session = _FakeSession(records=records)

    result = person.get_person_mails(session, "p1")

    # senza DISTINCT lato Cypher (qui simulato dalla fake session) il
    # duplicato non verrebbe rimosso: la garanzia di unicità è delegata
    # interamente alla query, come verificato sopra.
    assert len(result) == 2
    assert result[0] == result[1]


# --- get_person_addresses -------------------------------------------------------


def test_get_person_addresses_query_references_correct_labels_and_relationship():
    session = _FakeSession(records=[])

    person.get_person_addresses(session, "p1")

    assert len(session.calls) == 1
    query, params = session.calls[0]
    assert "Person" in query
    assert "EmailAddress" in query
    assert "OWNS" in query
    assert "DISTINCT e.address" in query
    assert params == {"person_id": "p1"}


def test_get_person_addresses_parses_records_into_dicts_sorted_by_address():
    records = [
        {"address": "b@example.com", "domain": "example.com", "is_redacted": False},
        {"address": "a@example.com", "domain": "example.com", "is_redacted": True},
    ]
    session = _FakeSession(records=records)

    result = person.get_person_addresses(session, "p1")

    assert result == [
        {"address": "a@example.com", "domain": "example.com", "is_redacted": True},
        {"address": "b@example.com", "domain": "example.com", "is_redacted": False},
    ]


# --- get_connected_persons -------------------------------------------------------


def test_get_connected_persons_query_references_correct_labels_and_relationships():
    session = _FakeSession(records=[])

    person.get_connected_persons(session, "p1")

    assert len(session.calls) == 1
    query, params = session.calls[0]
    assert "Person" in query
    assert "EmailAddress" in query
    assert "Mail" in query
    assert "OWNS" in query
    assert "SENT" in query
    assert "TO" in query
    assert "CC" in query
    assert "BCC" in query
    assert params == {"person_id": "p1"}


def test_get_connected_persons_query_excludes_self_and_dedups_on_person_id():
    session = _FakeSession(records=[])

    person.get_connected_persons(session, "p1")

    query, _params = session.calls[0]
    assert query.count("p2.person_id <> $person_id") == 2
    assert query.count("DISTINCT p2.person_id") == 2


def test_get_connected_persons_parses_records_into_dicts_sorted_by_person_id():
    records = [
        {"person_id": "p3", "display_name": "Charlie"},
        {"person_id": "p2", "display_name": "Bob"},
    ]
    session = _FakeSession(records=records)

    result = person.get_connected_persons(session, "p1")

    assert result == [
        {"person_id": "p2", "display_name": "Bob"},
        {"person_id": "p3", "display_name": "Charlie"},
    ]


def test_get_connected_persons_with_duplicate_person_ids_from_fake_session():
    # Stesso ragionamento di test_get_person_mails_with_duplicate_ids_from_fake_session:
    # la fake session non esegue Cypher, quindi record duplicati in ingresso
    # (che nel DB reale non arriverebbero mai grazie a `DISTINCT p2.person_id`,
    # verificato sopra) restano duplicati nel risultato Python. La garanzia di
    # unicità è delegata interamente alla query Cypher.
    records = [
        {"person_id": "p2", "display_name": "Bob"},
        {"person_id": "p2", "display_name": "Bob"},
    ]
    session = _FakeSession(records=records)

    result = person.get_connected_persons(session, "p1")

    assert len(result) == 2
    assert result[0] == result[1]
