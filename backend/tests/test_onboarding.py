import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import auth as auth_module
from tests.conftest import make_valid_cnpj

PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_KEY = PRIVATE_KEY.public_key()


class JWKSClientFalso:
    def get_signing_key_from_jwt(self, token: str):
        class SigningKeyFalsa:
            key = PUBLIC_KEY

        return SigningKeyFalsa()


def _make_token(email="dono@empresa.com.br", sub=None):
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": sub or str(uuid.uuid4()),
        "email": email,
        "aud": "authenticated",
        "exp": agora + timedelta(hours=1),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="ES256")


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_onboarding_cria_empresa_e_vincula_usuario(client, monkeypatch, db_engine):
    monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())

    response = client.post(
        "/onboarding",
        json={
            "company_name": "Padaria do Bairro",
            "cnpj": make_valid_cnpj(10),
            "site_url": "https://padaria.com.br",
            "user_name": "Maria Dona",
        },
        headers=_headers(_make_token()),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["company"]["name"] == "Padaria do Bairro"
    assert body["user_id"]


def test_onboarding_sem_token_e_401(client, db_engine):
    response = client.post(
        "/onboarding",
        json={"company_name": "X", "cnpj": make_valid_cnpj(11), "user_name": "Y"},
    )

    assert response.status_code == 401


def test_onboarding_duas_vezes_para_o_mesmo_usuario_e_409(client, monkeypatch, db_engine):
    monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())
    user_id = str(uuid.uuid4())
    token = _make_token(sub=user_id)
    payload = {"company_name": "Padaria", "cnpj": make_valid_cnpj(12), "user_name": "Maria"}

    primeira = client.post("/onboarding", json=payload, headers=_headers(token))
    segunda = client.post(
        "/onboarding",
        json={**payload, "cnpj": make_valid_cnpj(13)},
        headers=_headers(token),
    )

    assert primeira.status_code == 201
    assert segunda.status_code == 409


def test_onboarding_usuario_recem_criado_consegue_usar_rota_protegida(
    client, monkeypatch, db_engine
):
    monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())
    token = _make_token()

    client.post(
        "/onboarding",
        json={"company_name": "Padaria", "cnpj": make_valid_cnpj(14), "user_name": "Maria"},
        headers=_headers(token),
    )

    resposta_scans = client.get("/scans", headers=_headers(token))

    assert resposta_scans.status_code == 200
    assert resposta_scans.json() == []


def test_users_me_devolve_403_antes_do_onboarding(client, monkeypatch, db_engine):
    monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())

    response = client.get("/users/me", headers=_headers(_make_token()))

    assert response.status_code == 403


def test_users_me_devolve_dados_apos_onboarding(client, monkeypatch, db_engine):
    monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())
    token = _make_token(email="dona@padaria.com.br")

    client.post(
        "/onboarding",
        json={"company_name": "Padaria", "cnpj": make_valid_cnpj(15), "user_name": "Maria"},
        headers=_headers(token),
    )

    response = client.get("/users/me", headers=_headers(token))

    assert response.status_code == 200
    assert response.json()["email"] == "dona@padaria.com.br"
