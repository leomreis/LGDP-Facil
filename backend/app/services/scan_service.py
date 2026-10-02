"""Orquestração de um scan: varre o site, grava achados e gera o relatório.

Roda fora do ciclo de request (BackgroundTasks ou RQ, ver `enqueue_scan`), por
isso `run_scan` abre e fecha a própria sessão de banco: a sessão da requisição
já foi encerrada quando esta função começa a executar.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import BackgroundTasks

from app.core.config import Settings
from app.core.database import SessionLocal
from app.models.company import Company
from app.models.reports import Report
from app.models.scan_findings import ScanFinding
from app.models.scans import Scan, ScanStatusEnum
from app.scanner.crawler import crawl_site
from app.services.ai_provider import get_ai_provider
from app.services.report_generator import calculate_score, generate_executive_summary

logger = logging.getLogger(__name__)


def enqueue_scan(scan_id: uuid.UUID, background_tasks: BackgroundTasks, settings: Settings) -> None:
    """Decide como o scan vai rodar fora do request: RQ se REDIS_URL está
    configurada, BackgroundTasks do FastAPI caso contrário.

    Import de app.core.queue fica local para não exigir Redis instalado/rodando
    em ambientes que nunca configuram REDIS_URL (ex.: dev local sem Docker).
    """
    if settings.redis_url:
        from app.core.queue import get_queue

        get_queue().enqueue(run_scan, scan_id)
    else:
        background_tasks.add_task(run_scan, scan_id)


def run_scan(scan_id: uuid.UUID) -> None:
    """Executa o scan de ponta a ponta. Nunca levanta exceção para o chamador.

    Um scan que falha precisa terminar com status `failed` no banco, e não como
    uma exceção perdida numa thread de background que deixaria o scan preso
    para sempre em `in_progress`.
    """
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan is None:
            logger.error("Scan %s não encontrado", scan_id)
            return

        scan.status = ScanStatusEnum.in_progress
        db.commit()

        try:
            _executar(db, scan)
            scan.status = ScanStatusEnum.completed
        except Exception:
            logger.exception("Scan %s falhou", scan_id)
            scan.status = ScanStatusEnum.failed

        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _executar(db, scan: Scan) -> None:
    resultado = crawl_site(str(scan.url))

    for achado in resultado.findings:
        db.add(
            ScanFinding(
                scan_id=scan.id,
                finding_type=achado.finding_type,
                categoria_dado_pessoal=achado.category,
                risk=achado.risk,
                location=achado.location,
            )
        )
    db.commit()

    findings = db.query(ScanFinding).filter(ScanFinding.scan_id == scan.id).all()
    company = db.query(Company).filter(Company.id == scan.company_id).first()
    nome_empresa = company.name if company else "empresa"

    resumo = generate_executive_summary(
        get_ai_provider(),
        nome_empresa,
        str(scan.url),
        findings,
    )

    db.add(
        Report(
            scan_id=scan.id,
            score_conformidade=calculate_score(findings),
            resumo_executivo=resumo,
        )
    )
    db.commit()
