"""Schemi Pydantic per le risposte degli endpoint su `/persons`."""

from __future__ import annotations

from pydantic import BaseModel


class PersonMailOut(BaseModel):
    id: str
    subject: str | None = None
    sent_at: str | None = None


class ConnectedPersonOut(BaseModel):
    person_id: str
    display_name: str | None = None


class PersonAddressOut(BaseModel):
    address: str
    domain: str | None = None
    is_redacted: bool
