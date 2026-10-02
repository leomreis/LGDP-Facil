"""Testes de integração de POST /scans: cria a linha no banco e enfileira o
processamento (RQ se REDIS_URL configurada, senão BackgroundTasks — ver
enqueue_scan). O processamento em si (run_scan) é testado à parte."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import auth as auth_module
from app.core.config import get_settings
from tests.conftest import make_valid_cnpj

PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_KEY = PRIVATE_KEY.public_key()


class JWKSClientFalso:
    def get_signing_key_from_jwt(self, token: str):
        class SigningKeyFalsa:
            key = PUBLIC_KEY

        return SigningKeyFalsa()


def _make_token(email="dono@empresa.com.br"):
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": email,
        "aud": "authenticated",
        "exp": agora + timedelta(hours=1),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="ES256")


def _onboard_and_get_token(client, monkeypatch):
    monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())
    token = _make_token()
    client.post(
        "/onboarding",
        json={"company_name": "Padaria", "cnpj": make_valid_cnpj(20), "user_name": "Maria"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token


def test_post_scans_cria_scan_pendente_e_devolve_202(client, monkeypatch, db_engine):
    token = _onboard_and_get_token(client, monkeypatch)

    response = client.post(
        "/scans",
        json={"url": "https://exemplo.com.br"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["url"] == "https://exemplo.com.br/"
    assert body["status"] in ("pending", "in_progress")

    if get_settings().redis_url:
        from app.core.queue import get_queue

        get_queue().connection.flushdb()


def test_scan_criado_aparece_na_listagem(client, monkeypatch, db_engine):
    token = _onboard_and_get_token(client, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/scans", json={"url": "https://exemplo.com.br"}, headers=headers)
    resposta = client.get("/scans", headers=headers)

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1

    if get_settings().redis_url:
        from app.core.queue import get_queue

        get_queue().connection.flushdb()


def test_post_scans_devolve_429_apos_exceder_o_limite_por_empresa(client, monkeypatch, db_engine):
    token = _onboard_and_get_token(client, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}

    respostas = [
        client.post("/scans", json={"url": f"https://exemplo{i}.com.br"}, headers=headers)
        for i in range(6)
    ]

    assert [r.status_code for r in respostas[:5]] == [202] * 5
    assert respostas[5].status_code == 429

    if get_settings().redis_url:
        from app.core.queue import get_queue

        get_queue().connection.flushdb()
