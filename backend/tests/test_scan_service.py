"""Testes de run_scan/enqueue_scan de ponta a ponta, incluindo o processamento
real por um worker RQ (modo burst: processa o que está na fila e para) — não só
o enfileiramento. Nenhum teste toca a rede: `crawl_site` é chamado através do
crawler real, mas `fetch_page` é substituído por uma página fabricada."""

import uuid

import pytest
from rq import SimpleWorker

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.company import Company
from app.models.reports import Report
from app.models.scan_findings import ScanFinding
from app.models.scans import Scan, ScanStatusEnum
from app.scanner import crawler
from app.scanner.crawler import PageResponse
from app.services.ai_provider import FakeProvider
from app.services.scan_service import run_scan
from tests.conftest import make_valid_cnpj

FORMULARIO_HTML = """
<html><body>
  <form>
    <label for="cpf">CPF</label>
    <input type="text" id="cpf" name="cpf">
  </form>
</body></html>
"""


@pytest.fixture
def scan_pendente(db_engine):
    db = SessionLocal()
    cnpj_unico = str(uuid.uuid4().int)[:14]
    company = Company(name="Padaria", cnpj=cnpj_unico)
    db.add(company)
    db.flush()
    scan = Scan(company_id=company.id, url="https://exemplo.com.br", status=ScanStatusEnum.pending)
    db.add(scan)
    db.commit()
    scan_id = scan.id
    db.close()
    return scan_id


def test_run_scan_processa_achados_e_gera_relatorio(scan_pendente, monkeypatch):
    monkeypatch.setattr(crawler, "fetch_page", lambda url: PageResponse(html=FORMULARIO_HTML))
    monkeypatch.setattr("app.services.scan_service.get_ai_provider", lambda: FakeProvider())

    run_scan(scan_pendente)

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_pendente).first()
        assert scan.status == ScanStatusEnum.completed
        assert scan.completed_at is not None

        findings = db.query(ScanFinding).filter(ScanFinding.scan_id == scan_pendente).all()
        assert len(findings) == 1
        assert findings[0].categoria_dado_pessoal.value == "cpf"

        report = db.query(Report).filter(Report.scan_id == scan_pendente).first()
        assert report is not None
        assert report.score_conformidade < 100
    finally:
        db.close()


def test_run_scan_marca_failed_quando_o_crawler_explode(scan_pendente, monkeypatch):
    def _explode(url):
        raise RuntimeError("timeout de rede")

    monkeypatch.setattr(crawler, "fetch_page", _explode)
    monkeypatch.setattr("app.services.scan_service.get_ai_provider", lambda: FakeProvider())

    run_scan(scan_pendente)

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_pendente).first()
        assert scan.status == ScanStatusEnum.failed
        assert scan.completed_at is not None
    finally:
        db.close()


def test_run_scan_com_id_inexistente_nao_levanta_excecao():
    run_scan(uuid.uuid4())  # não deve lançar — só loga e retorna


class TestProcessamentoViaWorkerRQ:
    @pytest.fixture(autouse=True)
    def redis_disponivel(self):
        if not get_settings().redis_url:
            pytest.skip("REDIS_URL não configurada — teste pulado")

    def test_worker_processa_o_scan_enfileirado_de_ponta_a_ponta(self, scan_pendente, monkeypatch):
        """Prova o ciclo completo: enfileira no RQ, um worker de verdade consome e
        processa — não é só uma checagem de que o job foi aceito na fila."""
        from app.core.queue import get_queue

        monkeypatch.setattr(crawler, "fetch_page", lambda url: PageResponse(html=FORMULARIO_HTML))
        monkeypatch.setattr("app.services.scan_service.get_ai_provider", lambda: FakeProvider())

        fila = get_queue()
        fila.connection.flushdb()
        fila.enqueue(run_scan, scan_pendente)

        worker = SimpleWorker([fila], connection=fila.connection)
        worker.work(burst=True)

        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == scan_pendente).first()
            assert scan.status == ScanStatusEnum.completed
        finally:
            db.close()

        fila.connection.flushdb()


class TestPdfDaRotaDeRelatorio:
    def test_download_pdf_devolve_um_pdf_valido(self, client, monkeypatch, db_engine):
        from datetime import datetime, timedelta, timezone

        import jwt
        from cryptography.hazmat.primitives.asymmetric import ec

        from app.core import auth as auth_module

        chave_privada = ec.generate_private_key(ec.SECP256R1())
        chave_publica = chave_privada.public_key()

        class JWKSClientFalso:
            def get_signing_key_from_jwt(self, token: str):
                class SigningKeyFalsa:
                    key = chave_publica

                return SigningKeyFalsa()

        monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())
        agora = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "email": "x@x.com",
                "aud": "authenticated",
                "exp": agora + timedelta(hours=1),
            },
            chave_privada,
            algorithm="ES256",
        )
        headers = {"Authorization": f"Bearer {token}"}

        client.post(
            "/onboarding",
            json={"company_name": "Padaria", "cnpj": make_valid_cnpj(21), "user_name": "Maria"},
            headers=headers,
        )

        monkeypatch.setattr(crawler, "fetch_page", lambda url: PageResponse(html=FORMULARIO_HTML))
        monkeypatch.setattr("app.services.scan_service.get_ai_provider", lambda: FakeProvider())

        scan_resp = client.post("/scans", json={"url": "https://exemplo.com.br"}, headers=headers)
        scan_id = scan_resp.json()["id"]
        run_scan(uuid.UUID(scan_id))

        resposta = client.get(f"/reports/scan/{scan_id}/pdf", headers=headers)

        assert resposta.status_code == 200
        assert resposta.headers["content-type"] == "application/pdf"
        assert resposta.content.startswith(b"%PDF-")

    def test_download_pdf_de_scan_sem_relatorio_e_404(self, client, monkeypatch, db_engine):
        from datetime import datetime, timedelta, timezone

        import jwt
        from cryptography.hazmat.primitives.asymmetric import ec

        from app.core import auth as auth_module

        chave_privada = ec.generate_private_key(ec.SECP256R1())
        chave_publica = chave_privada.public_key()

        class JWKSClientFalso:
            def get_signing_key_from_jwt(self, token: str):
                class SigningKeyFalsa:
                    key = chave_publica

                return SigningKeyFalsa()

        monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())
        agora = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "email": "y@y.com",
                "aud": "authenticated",
                "exp": agora + timedelta(hours=1),
            },
            chave_privada,
            algorithm="ES256",
        )
        headers = {"Authorization": f"Bearer {token}"}

        client.post(
            "/onboarding",
            json={"company_name": "Padaria 2", "cnpj": make_valid_cnpj(22), "user_name": "João"},
            headers=headers,
        )

        resposta = client.get(f"/reports/scan/{uuid.uuid4()}/pdf", headers=headers)

        assert resposta.status_code == 404
