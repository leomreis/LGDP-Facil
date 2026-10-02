import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_authenticated_claims
from app.core.database import get_db
from app.models.company import Company
from app.models.users import User
from app.schemas.company import CompanyResponse
from app.schemas.onboarding import OnboardingCreate, OnboardingResponse

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
def onboard_company(
    payload: OnboardingCreate,
    claims: dict = Depends(get_authenticated_claims),
    db: Session = Depends(get_db),
):
    """Primeiro passo depois do cadastro no Supabase Auth: cria a empresa e
    vincula o usuário autenticado a ela. Sem isso, o token é válido mas
    `get_current_user` sempre devolve 403 — não existe linha em `users`.
    """
    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        ) from erro
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token não contém e-mail do usuário",
        )

    if db.query(User).filter(User.id == user_id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário já concluiu o onboarding",
        )

    company = Company(
        name=payload.company_name,
        cnpj=payload.cnpj,
        site_url=payload.site_url,
        software_name=payload.software_name,
    )
    db.add(company)
    db.flush()  # gera company.id sem fechar a transação, para o User referenciar

    user = User(
        id=user_id,
        company_id=company.id,
        name=payload.user_name,
        email=email,
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(company)

    return OnboardingResponse(company=CompanyResponse.model_validate(company), user_id=str(user_id))
