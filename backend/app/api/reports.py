import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.company import Company
from app.models.reports import Report
from app.models.scan_findings import ScanFinding
from app.models.scans import Scan
from app.models.users import User
from app.schemas.report import ReportResponse
from app.services.pdf_generator import generate_report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/scan/{scan_id}", response_model=ReportResponse)
def get_report_by_scan(
    scan_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """O relatório é criado pelo worker ao final do scan; antes disso, 404."""
    report = (
        db.query(Report)
        .join(Scan, Scan.id == Report.scan_id)
        .filter(Report.scan_id == scan_id, Scan.company_id == current_user.company_id)
        .first()
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relatório ainda não disponível para este scan",
        )

    return report


def _get_report_or_404(scan_id: uuid.UUID, db: Session, current_user: User) -> tuple[Report, Scan]:
    resultado = (
        db.query(Report, Scan)
        .join(Scan, Scan.id == Report.scan_id)
        .filter(Report.scan_id == scan_id, Scan.company_id == current_user.company_id)
        .first()
    )
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relatório ainda não disponível para este scan",
        )
    return resultado._tuple()


@router.get("/scan/{scan_id}/pdf")
def download_report_pdf(
    scan_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera e devolve o PDF do relatório na hora — não é um arquivo salvo."""
    report, scan = _get_report_or_404(scan_id, db, current_user)

    findings = db.query(ScanFinding).filter(ScanFinding.scan_id == scan.id).all()
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    nome_empresa = company.name if company else str(current_user.company_id)

    pdf_bytes = generate_report_pdf(
        company_name=nome_empresa,
        scan_url=scan.url,
        score=report.score_conformidade,
        resumo_executivo=report.resumo_executivo,
        findings=findings,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="relatorio-{scan_id}.pdf"',
        },
    )
