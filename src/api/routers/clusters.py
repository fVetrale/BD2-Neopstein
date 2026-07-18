from fastapi import APIRouter, Depends, Query
from neo4j import Session

from src.api.deps import get_session
from src.api.schemas.cluster import ClusterMailOut, ClusterPersonOut, TopRedactedClusterOut
from src.queries.cluster import get_cluster_mails, get_cluster_persons, get_top_redacted_clusters

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("/top-redacted", response_model=list[TopRedactedClusterOut])
def top_redacted_clusters(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_top_redacted_clusters(session, limit=offset + limit)
    return rows[offset : offset + limit]


@router.get("/{cluster_id}/mails", response_model=list[ClusterMailOut])
def cluster_mails(
    cluster_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_cluster_mails(session, cluster_id)
    return rows[offset : offset + limit]


@router.get("/{cluster_id}/persons", response_model=list[ClusterPersonOut])
def cluster_persons(
    cluster_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_cluster_persons(session, cluster_id)
    return rows[offset : offset + limit]
