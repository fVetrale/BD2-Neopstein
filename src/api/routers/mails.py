from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Session
from neo4j.exceptions import ConstraintError

from src.api.deps import get_session
from src.api.schemas.mail import MailCreate, MailInfoOut, MailOut, MailPersonOut, MailUpdate
from src.crud.mail import create_mail, delete_mail, update_mail
from src.queries.mail import get_mail_info, get_mail_persons

router = APIRouter(prefix="/mails", tags=["mails"])


@router.get(
    "/{mail_id}",
    response_model=MailInfoOut,
    summary="Dettaglio di una mail",
    description="Restituisce le proprietà della mail e, se presente, il cluster a cui appartiene con relativa probability.",
)
def mail_info(mail_id: str, session: Session = Depends(get_session)):
    info = get_mail_info(session, mail_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Mail '{mail_id}' non trovata")
    return info


@router.get(
    "/{mail_id}/persons",
    response_model=list[MailPersonOut],
    summary="Persone collegate a una mail",
    description="Restituisce le persone coinvolte nella mail con il relativo ruolo (sender/to/cc/bcc).",
)
def mail_persons(
    mail_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_mail_persons(session, mail_id)
    return rows[offset : offset + limit]


@router.post(
    "",
    response_model=MailOut,
    status_code=201,
    summary="Crea una mail",
    description="Crea un nuovo nodo `Mail` con le proprietà fornite; restituisce 409 se l'id esiste già.",
)
def create_mail_endpoint(payload: MailCreate, session: Session = Depends(get_session)):
    try:
        return create_mail(session, payload.model_dump())
    except ConstraintError:
        raise HTTPException(status_code=409, detail=f"Mail '{payload.id}' già esistente")


@router.put(
    "/{mail_id}",
    response_model=MailOut,
    summary="Aggiorna una mail",
    description="Aggiorna le proprietà del nodo `Mail` indicato; restituisce 404 se non esiste.",
)
def update_mail_endpoint(mail_id: str, payload: MailUpdate, session: Session = Depends(get_session)):
    updated = update_mail(session, mail_id, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Mail '{mail_id}' non trovata")
    return updated


@router.delete(
    "/{mail_id}",
    status_code=204,
    summary="Elimina una mail",
    description="Elimina il nodo `Mail` indicato e le relazioni collegate; restituisce 404 se non esiste.",
)
def delete_mail_endpoint(mail_id: str, session: Session = Depends(get_session)):
    deleted = delete_mail(session, mail_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Mail '{mail_id}' non trovata")
