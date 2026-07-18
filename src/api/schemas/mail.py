"""Schemi Pydantic per le risposte degli endpoint su `/mails`."""

from __future__ import annotations

from pydantic import BaseModel


class MailInfoOut(BaseModel):
    id: str
    subject: str | None = None
    sent_at: str | None = None
    redaction_count: int | None = None
    redaction_ratio: float | None = None
    attachment_count: int | None = None
    is_promotional: bool | None = None
    cluster_id: int | None = None
    label: str | None = None
    probability: float | None = None


class MailPersonOut(BaseModel):
    person_id: str
    display_name: str | None = None
    is_unknown: bool
    is_epstein: bool
    roles: list[str]
