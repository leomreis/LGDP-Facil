import re

from pydantic import BaseModel, field_validator

from app.core.validators import is_valid_cnpj
from app.schemas.company import CompanyResponse


class OnboardingCreate(BaseModel):
    """Cadastro de empresa vinculado ao usuário já autenticado no Supabase.

    name/email do usuário não vêm daqui: o nome vem do próprio cadastro de
    equipe (name) e o e-mail vem do claim do token — nunca do que o cliente
    manda, para não permitir que alguém se cadastre com e-mail de outra pessoa.
    """

    company_name: str
    cnpj: str
    site_url: str | None = None
    software_name: str | None = None
    user_name: str

    @field_validator("cnpj")
    @classmethod
    def valida_cnpj(cls, valor: str) -> str:
        if not is_valid_cnpj(valor):
            raise ValueError("CNPJ inválido")
        return re.sub(r"\D", "", valor)


class OnboardingResponse(BaseModel):
    company: CompanyResponse
    user_id: str
