"""Entity resolution di Person a partire dai display name grezzi.

Union-find deterministico su (nome, indirizzo) raccolti da sender/to/cc/bcc:
match esatto su nome normalizzato, match cognome+iniziale (entrambi gli
ordinamenti), indirizzo non-redacted condiviso (vedi CLAUDE.md, sezione
Regole ETL). Nessuna adjudication automatica: i gruppi residui ambigui
restano Person distinte.

Nessun I/O su parquet qui: pipeline pura, testabile standalone.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")

REDACTED_PREFIX = "redacted:"


def normalize_name(name: str) -> str:
    """Lowercase, trim, collassa whitespace, rimuove punteggiatura."""
    normalized = name.lower().strip()
    normalized = _PUNCT_RE.sub("", normalized)
    normalized = _WS_RE.sub(" ", normalized).strip()
    return normalized


def surname_initial_keys(normalized_name: str) -> set[tuple[str, str]]:
    """Chiavi (cognome, iniziale) candidate per entrambi gli ordinamenti.

    "First Last" -> (last_token, first_token[0])
    "Last First" -> (first_token, last_token[0])
    """
    tokens = normalized_name.split()
    if len(tokens) < 2:
        return set()
    first_token, last_token = tokens[0], tokens[-1]
    return {
        (last_token, first_token[0]),
        (first_token, last_token[0]),
    }


def _is_degenerate(normalized_name: str) -> bool:
    """Nome troppo corto/degenerato per essere considerato reale."""
    if len(normalized_name) < 2:
        return True
    if not any(c.isalpha() for c in normalized_name):
        return True
    return False


class _DisjointSet:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        self._parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


@dataclass
class PersonRecord:
    person_id: str
    display_name: str
    is_unknown: bool
    is_epstein: bool


@dataclass
class ResolutionResult:
    raw_name_to_person_id: dict[str, str] = field(default_factory=dict)
    persons: list[PersonRecord] = field(default_factory=list)
    resolved_by_rules: int = 0
    is_unknown: int = 0


def resolve_persons(
    mentions: list[tuple[str, str]],
    epstein_sender_addresses: set[str] | None = None,
) -> ResolutionResult:
    """Risolve le identità Person a partire dalle menzioni (nome, indirizzo).

    `mentions` deve già escludere le entry con nome None (issue #16 punto 8):
    quell'indirizzo esiste comunque come EmailAddress ma non entra qui.
    """
    epstein_sender_addresses = epstein_sender_addresses or set()

    raw_variants: dict[str, Counter] = defaultdict(Counter)
    norm_addr: dict[str, set[str]] = defaultdict(set)
    norm_names: set[str] = set()

    for name, address in mentions:
        if name is None:
            continue
        normalized = normalize_name(name)
        if not normalized:
            continue
        raw_variants[normalized][name] += 1
        norm_addr[normalized].add(address)
        norm_names.add(normalized)

    dsu = _DisjointSet()
    for n in norm_names:
        dsu.add(n)

    # Step 2: surname + initial keys, entrambi gli ordinamenti.
    key_index: dict[tuple[str, str], list[str]] = defaultdict(list)
    for n in norm_names:
        for key in surname_initial_keys(n):
            key_index[key].append(n)
    for names in key_index.values():
        if len(names) > 1:
            for other in names[1:]:
                dsu.union(names[0], other)

    # Step 3: indirizzo non-redacted condiviso tra gruppi.
    addr_group_index: dict[str, set[str]] = defaultdict(set)
    for n in norm_names:
        root = dsu.find(n)
        for addr in norm_addr[n]:
            if not addr.startswith(REDACTED_PREFIX):
                addr_group_index[addr].add(root)
    for roots in addr_group_index.values():
        if len(roots) > 1:
            roots_list = sorted(roots)
            for other in roots_list[1:]:
                dsu.union(roots_list[0], other)

    # Gruppi finali (post regole 1-3): i residui ambigui restano Person distinte.
    final_groups: dict[str, list[str]] = defaultdict(list)
    for n in norm_names:
        final_groups[dsu.find(n)].append(n)

    result = ResolutionResult()
    for members in final_groups.values():
        combined_counter: Counter = Counter()
        combined_addrs: set[str] = set()
        for m in members:
            combined_counter.update(raw_variants[m])
            combined_addrs |= norm_addr[m]

        top_raw_name = sorted(combined_counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        person_id = normalize_name(top_raw_name)
        display_name = top_raw_name

        unknown = _is_degenerate(person_id)
        is_epstein = bool(combined_addrs & epstein_sender_addresses)

        result.resolved_by_rules += 1
        if unknown:
            result.is_unknown += 1

        result.persons.append(
            PersonRecord(
                person_id=person_id,
                display_name=display_name,
                is_unknown=unknown,
                is_epstein=is_epstein,
            )
        )

        for m in members:
            for raw in raw_variants[m]:
                result.raw_name_to_person_id[raw] = person_id

    return result
