import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.policy_documents import PolicyDocumentStatus, PolicyDocumentType


class PolicyDocumentCreate(BaseModel):
    """Gera um rascunho a partir do scan mais recente da empresa.

    scan_id explícito (em vez de "o último scan") torna o resultado reprodutível:
    o mesmo scan_id sempre gera a partir do mesmo conjunto de achados.
    """

    tipo: PolicyDocumentType
    scan_id: uuid.UUID


class PolicyDocumentResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    tipo: PolicyDocumentType
    content: str
    version: str
    status: PolicyDocumentStatus
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PublicPolicyDocumentResponse(BaseModel):
    """O que a página pública mostra — sem id, company_id nem status: o
    visitante do site da empresa não precisa (nem deve) ver dado interno."""

    company_name: str
    tipo: PolicyDocumentType
    version: str
    content: str
    created_at: datetime | None = None


class PolicyDocumentPublish(BaseModel):
    status: PolicyDocumentStatus
