from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Session

from src.api.deps import get_session
from src.api.schemas.mail import MailInfoOut, MailPersonOut
from src.queries.mail import get_mail_info, get_mail_persons

router = APIRouter(prefix="/mails", tags=["mails"])


@router.get("/{mail_id}", response_model=MailInfoOut)
def mail_info(mail_id: str, session: Session = Depends(get_session)):
    info = get_mail_info(session, mail_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Mail '{mail_id}' non trovata")
    return info


@router.get("/{mail_id}/persons", response_model=list[MailPersonOut])
def mail_persons(
    mail_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_mail_persons(session, mail_id)
    return rows[offset : offset + limit]
