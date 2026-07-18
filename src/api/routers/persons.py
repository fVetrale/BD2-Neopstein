from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Session
from neo4j.exceptions import ConstraintError

from src.api.deps import get_session
from src.api.schemas.person import (
    ConnectedPersonOut,
    PersonAddressOut,
    PersonCreate,
    PersonMailOut,
    PersonOut,
    PersonUpdate,
)
from src.crud.person import create_person, delete_person, get_person, update_person
from src.queries.person import get_connected_persons, get_person_addresses, get_person_mails

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get(
    "/{person_id}/mails",
    response_model=list[PersonMailOut],
    summary="Mail di una persona",
    description="Restituisce le mail inviate o ricevute dalla persona indicata.",
)
def person_mails(
    person_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_person_mails(session, person_id)
    return rows[offset : offset + limit]


@router.get(
    "/{person_id}/connected",
    response_model=list[ConnectedPersonOut],
    summary="Persone connesse",
    description="Restituisce le persone connesse alla persona indicata tramite scambio di email.",
)
def person_connected(
    person_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_connected_persons(session, person_id)
    return rows[offset : offset + limit]


@router.get(
    "/{person_id}/addresses",
    response_model=list[PersonAddressOut],
    summary="Indirizzi email di una persona",
    description="Restituisce gli indirizzi email posseduti dalla persona indicata.",
)
def person_addresses(
    person_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_person_addresses(session, person_id)
    return rows[offset : offset + limit]


@router.post(
    "",
    response_model=PersonOut,
    status_code=201,
    summary="Crea una persona",
    description="Crea un nuovo nodo `Person` con le proprietà fornite; restituisce 409 se l'id esiste già.",
)
def create_person_endpoint(payload: PersonCreate, session: Session = Depends(get_session)):
    try:
        return create_person(session, payload.model_dump())
    except ConstraintError:
        raise HTTPException(status_code=409, detail=f"Person '{payload.person_id}' già esistente")


@router.get(
    "/{person_id}",
    response_model=PersonOut,
    summary="Dettaglio di una persona",
    description="Restituisce le proprietà del nodo `Person` indicato; 404 se non esiste.",
)
def person_info(person_id: str, session: Session = Depends(get_session)):
    person = get_person(session, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail=f"Person '{person_id}' non trovata")
    return person


@router.put(
    "/{person_id}",
    response_model=PersonOut,
    summary="Aggiorna una persona",
    description="Aggiorna le proprietà del nodo `Person` indicato; restituisce 404 se non esiste.",
)
def update_person_endpoint(person_id: str, payload: PersonUpdate, session: Session = Depends(get_session)):
    updated = update_person(session, person_id, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Person '{person_id}' non trovata")
    return updated


@router.delete(
    "/{person_id}",
    status_code=204,
    summary="Elimina una persona",
    description="Elimina il nodo `Person` indicato e le relazioni collegate; restituisce 404 se non esiste.",
)
def delete_person_endpoint(person_id: str, session: Session = Depends(get_session)):
    deleted = delete_person(session, person_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Person '{person_id}' non trovata")
