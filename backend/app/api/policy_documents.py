import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.models.company import Company
from app.models.policy_documents import PolicyDocument, PolicyDocumentStatus
from app.models.scan_findings import ScanFinding
from app.models.scans import Scan
from app.models.users import User
from app.schemas.policy_document import (
    PolicyDocumentCreate,
    PolicyDocumentPublish,
    PolicyDocumentResponse,
)
from app.services.ai_provider import AIProviderError, get_ai_provider
from app.services.policy_generator import generate_policy_content, next_version

router = APIRouter(prefix="/policy-documents", tags=["policy-documents"])


@router.post("", response_model=PolicyDocumentResponse, status_code=status.HTTP_201_CREATED)
def create_policy_document(
    payload: PolicyDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Gera um rascunho de política/aviso a partir dos achados de um scan da empresa.

    Limitado por empresa: cada chamada aqui é uma chamada de IA (Gemini/Anthropic),
    que tem cota e/ou custo — sem limite, "gerar de novo" repetido esgotaria a
    cota do provedor rapidinho.
    """
    check_rate_limit(
        f"policy:{current_user.company_id}", max_calls=10, window_seconds=3600, settings=settings
    )

    scan = (
        db.query(Scan)
        .filter(Scan.id == payload.scan_id, Scan.company_id == current_user.company_id)
        .first()
    )
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan não encontrado")

    findings = db.query(ScanFinding).filter(ScanFinding.scan_id == scan.id).all()
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    nome_empresa = company.name if company else str(current_user.company_id)

    try:
        content = generate_policy_content(
            get_ai_provider(),
            payload.tipo,
            nome_empresa,
            scan.url,
            findings,
        )
    except AIProviderError as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Não foi possível gerar o documento agora: {erro}",
        ) from erro

    versoes_anteriores = [
        pd.version
        for pd in db.query(PolicyDocument)
        .filter(
            PolicyDocument.company_id == current_user.company_id,
            PolicyDocument.tipo == payload.tipo,
        )
        .all()
    ]

    documento = PolicyDocument(
        company_id=current_user.company_id,
        tipo=payload.tipo,
        content=content,
        version=next_version(versoes_anteriores),
        status=PolicyDocumentStatus.DRAFT,
    )
    db.add(documento)
    db.commit()
    db.refresh(documento)

    return documento


@router.get("", response_model=list[PolicyDocumentResponse])
def list_policy_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(PolicyDocument)
        .filter(PolicyDocument.company_id == current_user.company_id)
        .order_by(PolicyDocument.created_at.desc())
        .all()
    )


@router.patch("/{document_id}", response_model=PolicyDocumentResponse)
def update_policy_document_status(
    document_id: uuid.UUID,
    payload: PolicyDocumentPublish,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publica (ou volta a rascunho) um documento já gerado."""
    documento = (
        db.query(PolicyDocument)
        .filter(
            PolicyDocument.id == document_id,
            PolicyDocument.company_id == current_user.company_id,
        )
        .first()
    )
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado"
        )

    documento.status = payload.status
    db.commit()
    db.refresh(documento)

    return documento
