import re
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.core.validators import is_valid_cnpj


class CompanyCreate(BaseModel):
    """O que o cliente envia ao criar uma empresa — sem id nem created_at."""

    name: str
    cnpj: str
    site_url: str | None = None
    software_name: str | None = None

    @field_validator("cnpj")
    @classmethod
    def valida_cnpj(cls, valor: str) -> str:
        """Rejeita CNPJ com dígito verificador incorreto e normaliza para
        14 dígitos sem pontuação — a mesma empresa não pode ser cadastrada
        duas vezes só porque digitou o CNPJ com ou sem máscara."""
        if not is_valid_cnpj(valor):
            raise ValueError("CNPJ inválido")
        return re.sub(r"\D", "", valor)


class CompanyResponse(BaseModel):
    """O que a API devolve — inclui os campos gerados pelo banco."""

    id: uuid.UUID
    name: str
    cnpj: str
    site_url: str | None = None
    software_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
