from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyResponse

router = APIRouter()


@router.post("/companies", response_model=CompanyResponse)
def create_company(company_data: CompanyCreate, db: Session = Depends(get_db)):
    new_company = Company(
        name=company_data.name,
        cnpj=company_data.cnpj,
        site_url=company_data.site_url,
        software_name=company_data.software_name,
    )

    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return new_company
