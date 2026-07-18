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


class MailCreate(BaseModel):
    """Corpo per `POST /mails`: proprietà del nodo `Mail` da creare."""

    id: str
    subject: str | None = None
    body: str | None = None
    sent_at: str | None = None
    redaction_count: int | None = None
    redaction_ratio: float | None = None
    attachment_count: int | None = None
    is_promotional: bool | None = None


class MailUpdate(BaseModel):
    """Corpo per `PUT /mails/{mail_id}`: campi opzionali, `id` esclusa (è nel path)."""

    subject: str | None = None
    body: str | None = None
    sent_at: str | None = None
    redaction_count: int | None = None
    redaction_ratio: float | None = None
    attachment_count: int | None = None
    is_promotional: bool | None = None


class MailOut(BaseModel):
    """Risposta per create/read/update di `Mail` (solo proprietà del nodo, senza cluster)."""

    id: str
    subject: str | None = None
    body: str | None = None
    sent_at: str | None = None
    redaction_count: int | None = None
    redaction_ratio: float | None = None
    attachment_count: int | None = None
    is_promotional: bool | None = None
