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


class PersonCreate(BaseModel):
    """Corpo per `POST /persons`: proprietà del nodo `Person` da creare."""

    person_id: str
    display_name: str | None = None
    is_unknown: bool = False
    is_epstein: bool = False


class PersonUpdate(BaseModel):
    """Corpo per `PUT /persons/{person_id}`: campi opzionali, `person_id` esclusa (è nel path)."""

    display_name: str | None = None
    is_unknown: bool | None = None
    is_epstein: bool | None = None


class PersonOut(BaseModel):
    """Risposta per create/read/update di `Person` (solo proprietà del nodo)."""

    person_id: str
    display_name: str | None = None
    is_unknown: bool
    is_epstein: bool
