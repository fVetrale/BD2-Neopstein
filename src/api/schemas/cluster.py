"""Schemi Pydantic per le risposte degli endpoint su `/clusters`."""

from __future__ import annotations

from pydantic import BaseModel


class ClusterMailOut(BaseModel):
    id: str
    subject: str | None = None
    sent_at: str | None = None
    redaction_count: int | None = None
    probability: float | None = None


class ClusterPersonOut(BaseModel):
    person_id: str
    display_name: str | None = None
    is_unknown: bool
    is_epstein: bool


class TopRedactedClusterOut(BaseModel):
    cluster_id: int
    label: str | None = None
    total_redactions: int


class ClusterCreate(BaseModel):
    """Corpo per `POST /clusters`: proprietà del nodo `Cluster` da creare."""

    cluster_id: int
    label: str | None = None


class ClusterUpdate(BaseModel):
    """Corpo per `PUT /clusters/{cluster_id}`: unico campo aggiornabile è `label`."""

    label: str | None = None


class ClusterOut(BaseModel):
    """Risposta per create/read/update di `Cluster` (solo proprietà del nodo)."""

    cluster_id: int
    label: str | None = None
