from fastapi import APIRouter, Depends, Query
from neo4j import Session

from src.api.deps import get_session
from src.api.schemas.person import ConnectedPersonOut, PersonAddressOut, PersonMailOut
from src.queries.person import get_connected_persons, get_person_addresses, get_person_mails

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("/{person_id}/mails", response_model=list[PersonMailOut])
def person_mails(
    person_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_person_mails(session, person_id)
    return rows[offset : offset + limit]


@router.get("/{person_id}/connected", response_model=list[ConnectedPersonOut])
def person_connected(
    person_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_connected_persons(session, person_id)
    return rows[offset : offset + limit]


@router.get("/{person_id}/addresses", response_model=list[PersonAddressOut])
def person_addresses(
    person_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_person_addresses(session, person_id)
    return rows[offset : offset + limit]
