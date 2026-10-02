"""Testes de /public: a única rota sem autenticação. O que importa aqui é que
rascunho e documento de outra empresa nunca vazem."""

import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import make_valid_cnpj


def _cria_empresa_com_documentos(documentos):
    """documentos: lista de (tipo, status, version, content, idade_em_dias)."""
    from app.core.database import SessionLocal
    from app.models.company import Company
    from app.models.policy_documents import PolicyDocument

    db = SessionLocal()
    try:
        empresa = Company(name="Padaria do Bairro", cnpj=make_valid_cnpj(uuid.uuid4().int))
        db.add(empresa)
        db.flush()
        agora = datetime.now(timezone.utc)
        for tipo, status, version, content, idade in documentos:
            db.add(
                PolicyDocument(
                    company_id=empresa.id,
                    tipo=tipo,
                    status=status,
                    version=version,
                    content=content,
                    created_at=agora - timedelta(days=idade),
                )
            )
        db.commit()
        return str(empresa.id)
    finally:
        db.close()


def _url(company_id, tipo="privacy_policy"):
    return f"/public/companies/{company_id}/policy-documents/{tipo}"


def test_devolve_a_versao_publicada_mais_recente(client, db_engine):
    from app.models.policy_documents import PolicyDocumentStatus as S
    from app.models.policy_documents import PolicyDocumentType as T

    company_id = _cria_empresa_com_documentos(
        [
            (T.PRIVACY_POLICY, S.PUBLISHED, "v1", "texto antigo", 10),
            (T.PRIVACY_POLICY, S.PUBLISHED, "v2", "texto atual", 5),
            (T.PRIVACY_POLICY, S.DRAFT, "v3", "rascunho secreto", 1),
        ]
    )

    resposta = client.get(_url(company_id))

    assert resposta.status_code == 200
    body = resposta.json()
    assert body["version"] == "v2"
    assert body["content"] == "texto atual"
    assert body["company_name"] == "Padaria do Bairro"
    assert "status" not in body
    assert "company_id" not in body


def test_so_rascunho_e_404(client, db_engine):
    from app.models.policy_documents import PolicyDocumentStatus as S
    from app.models.policy_documents import PolicyDocumentType as T

    company_id = _cria_empresa_com_documentos(
        [(T.PRIVACY_POLICY, S.DRAFT, "v1", "rascunho secreto", 1)]
    )

    resposta = client.get(_url(company_id))

    assert resposta.status_code == 404
    assert "rascunho secreto" not in resposta.text


def test_nao_mistura_tipos_de_documento(client, db_engine):
    from app.models.policy_documents import PolicyDocumentStatus as S
    from app.models.policy_documents import PolicyDocumentType as T

    company_id = _cria_empresa_com_documentos(
        [(T.COOKIE_NOTICE, S.PUBLISHED, "v1", "aviso de cookies", 1)]
    )

    assert client.get(_url(company_id, "privacy_policy")).status_code == 404
    assert client.get(_url(company_id, "cookie_notice")).status_code == 200


def test_empresa_inexistente_e_404(client, db_engine):
    assert client.get(_url(uuid.uuid4())).status_code == 404


def test_tipo_invalido_e_422(client, db_engine):
    assert client.get(_url(uuid.uuid4(), "contrato_secreto")).status_code == 422
