from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Session
from neo4j.exceptions import ConstraintError

from src.api.deps import get_session
from src.api.schemas.cluster import (
    ClusterCreate,
    ClusterMailOut,
    ClusterOut,
    ClusterPersonOut,
    ClusterUpdate,
    TopRedactedClusterOut,
)
from src.crud.cluster import create_cluster, delete_cluster, get_cluster, update_cluster
from src.queries.cluster import get_cluster_mails, get_cluster_persons, get_top_redacted_clusters

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get(
    "/top-redacted",
    response_model=list[TopRedactedClusterOut],
    summary="Classifica dei cluster per redazioni",
    description="Restituisce i cluster ordinati per numero totale di redazioni, in ordine decrescente.",
)
def top_redacted_clusters(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_top_redacted_clusters(session, limit=offset + limit)
    return rows[offset : offset + limit]


@router.post(
    "",
    response_model=ClusterOut,
    status_code=201,
    summary="Crea un cluster",
    description="Crea un nuovo nodo `Cluster` con le proprietà fornite; restituisce 409 se l'id esiste già.",
)
def create_cluster_endpoint(payload: ClusterCreate, session: Session = Depends(get_session)):
    try:
        return create_cluster(session, payload.model_dump())
    except ConstraintError:
        raise HTTPException(status_code=409, detail=f"Cluster '{payload.cluster_id}' già esistente")


@router.get(
    "/{cluster_id}/mails",
    response_model=list[ClusterMailOut],
    summary="Mail di un cluster",
    description="Restituisce le mail appartenenti al cluster, con la `probability` della relazione `BELONGS_TO`.",
)
def cluster_mails(
    cluster_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_cluster_mails(session, cluster_id)
    return rows[offset : offset + limit]


@router.get(
    "/{cluster_id}/persons",
    response_model=list[ClusterPersonOut],
    summary="Persone di un cluster",
    description="Restituisce le persone coinvolte (mittenti/destinatari) nelle mail del cluster.",
)
def cluster_persons(
    cluster_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    rows = get_cluster_persons(session, cluster_id)
    return rows[offset : offset + limit]


@router.get(
    "/{cluster_id}",
    response_model=ClusterOut,
    summary="Dettaglio di un cluster",
    description="Restituisce le proprietà del nodo `Cluster` indicato; 404 se non esiste.",
)
def cluster_info(cluster_id: int, session: Session = Depends(get_session)):
    cluster = get_cluster(session, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' non trovato")
    return cluster


@router.put(
    "/{cluster_id}",
    response_model=ClusterOut,
    summary="Aggiorna un cluster",
    description="Aggiorna la proprietà `label` del nodo `Cluster` indicato; restituisce 404 se non esiste.",
)
def update_cluster_endpoint(cluster_id: int, payload: ClusterUpdate, session: Session = Depends(get_session)):
    updated = update_cluster(session, cluster_id, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' non trovato")
    return updated


@router.delete(
    "/{cluster_id}",
    status_code=204,
    summary="Elimina un cluster",
    description="Elimina il nodo `Cluster` indicato e le relazioni collegate; restituisce 404 se non esiste.",
)
def delete_cluster_endpoint(cluster_id: int, session: Session = Depends(get_session)):
    deleted = delete_cluster(session, cluster_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' non trovato")
