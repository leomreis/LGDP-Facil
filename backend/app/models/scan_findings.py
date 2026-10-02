import enum
import uuid

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FindingType(str, enum.Enum):
    FORM = "form"
    COOKIES = "cookies"
    THIRD_PARTY_SCRIPT = "third_party_script"


class CategoryType(str, enum.Enum):
    cpf = "cpf"
    email = "email"
    phone = "phone"
    address = "address"
    full_name = "full_name"
    other = "other"


class RiskType(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ScanFinding(Base):
    __tablename__ = "scan_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False
    )
    finding_type: Mapped[FindingType] = mapped_column(
        SQLEnum(FindingType), nullable=False, default=FindingType.FORM
    )
    categoria_dado_pessoal: Mapped[CategoryType] = mapped_column(
        SQLEnum(CategoryType), nullable=False, default=CategoryType.cpf
    )
    risk: Mapped[RiskType] = mapped_column(SQLEnum(RiskType), nullable=False, default=RiskType.low)
    location: Mapped[str] = mapped_column(String, nullable=False)
