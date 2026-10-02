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


class PolicyDocumentPublish(BaseModel):
    status: PolicyDocumentStatus
