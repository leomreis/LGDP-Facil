"""Rotas sem autenticação: o que a empresa escolheu tornar público.

Hoje só a versão publicada mais recente de cada política, para a PME poder
linkar a página no rodapé do site em vez de copiar e colar o texto. Rascunhos
nunca saem por aqui — a rota filtra por status, não confia em nada do cliente.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limit import check_rate_limit
from app.models.company import Company
from app.models.policy_documents import (
    PolicyDocument,
    PolicyDocumentStatus,
    PolicyDocumentType,
)
from app.schemas.policy_document import PublicPolicyDocumentResponse

router = APIRouter(prefix="/public", tags=["public"])


@router.get(
    "/companies/{company_id}/policy-documents/{tipo}",
    response_model=PublicPolicyDocumentResponse,
)
def get_published_policy_document(
    company_id: uuid.UUID,
    tipo: PolicyDocumentType,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Versão publicada mais recente de um tipo de documento da empresa.

    Limitado por IP: é a única rota aberta a qualquer um na internet, e cada
    chamada é uma ida ao banco.
    """
    ip = request.client.host if request.client else "desconhecido"
    check_rate_limit(f"public:{ip}", max_calls=120, window_seconds=60, settings=settings)

    documento = (
        db.query(PolicyDocument)
        .filter(
            PolicyDocument.company_id == company_id,
            PolicyDocument.tipo == tipo,
            PolicyDocument.status == PolicyDocumentStatus.PUBLISHED,
        )
        .order_by(PolicyDocument.created_at.desc())
        .first()
    )
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado"
        )

    company = db.query(Company).filter(Company.id == company_id).first()

    return PublicPolicyDocumentResponse(
        company_name=company.name if company else "",
        tipo=documento.tipo,
        version=documento.version,
        content=documento.content,
        created_at=documento.created_at,
    )
