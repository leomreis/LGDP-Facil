import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.models.scan_findings import ScanFinding
from app.models.scans import Scan
from app.models.users import User
from app.schemas.scan import (
    ScanCreate,
    ScanDetailResponse,
    ScanFindingResponse,
    ScanResponse,
)
from app.services.scan_service import enqueue_scan

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
def create_scan(
    scan_data: ScanCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Enfileira um scan e devolve 202 — a varredura roda fora do request.

    Via RQ quando REDIS_URL está configurada, via BackgroundTasks caso
    contrário — a decisão é de `enqueue_scan` (app/services/scan_service.py).

    Limitado por empresa: cada scan varre até 20 páginas e termina chamando a
    IA, então é a rota mais cara da API — sem limite, um usuário só (mal-
    intencionado ou não) poderia esgotar a cota do provedor de IA sozinho.
    """
    check_rate_limit(
        f"scan:{current_user.company_id}", max_calls=5, window_seconds=60, settings=settings
    )

    scan = Scan(company_id=current_user.company_id, url=str(scan_data.url))
    db.add(scan)
    db.commit()
    db.refresh(scan)

    enqueue_scan(scan.id, background_tasks, settings)

    return scan


@router.get("", response_model=list[ScanResponse])
def list_scans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Scan)
        .filter(Scan.company_id == current_user.company_id)
        .order_by(Scan.created_at.desc())
        .all()
    )


@router.get("/{scan_id}", response_model=ScanDetailResponse)
def get_scan(
    scan_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Status e achados de um scan. 404 também para scan de outra empresa.

    Devolver 403 revelaria que aquele id existe — 404 não vaza nada.
    """
    scan = (
        db.query(Scan)
        .filter(Scan.id == scan_id, Scan.company_id == current_user.company_id)
        .first()
    )
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan não encontrado")

    findings = db.query(ScanFinding).filter(ScanFinding.scan_id == scan.id).all()

    return ScanDetailResponse(
        id=scan.id,
        company_id=scan.company_id,
        url=scan.url,
        status=scan.status,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        findings=[ScanFindingResponse.model_validate(f) for f in findings],
    )
