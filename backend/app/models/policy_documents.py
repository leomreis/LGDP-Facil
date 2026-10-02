import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class PolicyDocumentType(str, enum.Enum):
    PRIVACY_POLICY = "privacy_policy"
    TERMS_OF_USE = "terms_of_use"
    COOKIE_NOTICE = "cookie_notice"


class PolicyDocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    tipo: Mapped[PolicyDocumentType] = mapped_column(SQLEnum(PolicyDocumentType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PolicyDocumentStatus] = mapped_column(
        SQLEnum(PolicyDocumentStatus),
        nullable=False,
        default=PolicyDocumentStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
