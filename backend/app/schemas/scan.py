import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl

from app.models.scan_findings import CategoryType, FindingType, RiskType
from app.models.scans import ScanStatusEnum


class ScanCreate(BaseModel):
    """A empresa vem do usuário autenticado, não do corpo da requisição."""

    url: HttpUrl


class ScanFindingResponse(BaseModel):
    id: uuid.UUID
    finding_type: FindingType
    categoria_dado_pessoal: CategoryType
    risk: RiskType
    location: str

    class Config:
        from_attributes = True


class ScanResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    url: str
    status: ScanStatusEnum
    created_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class ScanDetailResponse(ScanResponse):
    findings: list[ScanFindingResponse] = []
