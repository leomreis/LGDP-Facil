"""Testes de auth.py contra chaves ES256 geradas localmente — nenhum teste aqui
toca a rede nem o JWKS real do Supabase. `_jwks_client` é substituído por um
fake cujo `get_signing_key_from_jwt` devolve a chave pública gerada no teste."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import auth as auth_module
from app.core.config import Settings

PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_KEY = PRIVATE_KEY.public_key()


@dataclass
class SigningKeyFalsa:
    key: object


class JWKSClientFalso:
    def get_signing_key_from_jwt(self, token: str) -> SigningKeyFalsa:
        return SigningKeyFalsa(key=PUBLIC_KEY)


@pytest.fixture(autouse=True)
def jwks_falso(monkeypatch):
    monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())


@pytest.fixture
def settings():
    s = Settings()
    s.supabase_jwks_url = "https://fake.supabase.co/jwks"
    s.jwt_audience = "authenticated"
    return s


def _make_token(*, sub=None, email="dono@empresa.com.br", expirado=False, audience="authenticated"):
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": sub or str(uuid.uuid4()),
        "email": email,
        "aud": audience,
        "exp": agora - timedelta(minutes=5) if expirado else agora + timedelta(hours=1),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="ES256")


class TestDecodeToken:
    def test_aceita_token_valido_assinado_com_es256(self, settings):
        token = _make_token()

        claims = auth_module.decode_token(token, settings)

        assert claims["email"] == "dono@empresa.com.br"

    def test_rejeita_token_expirado(self, settings):
        token = _make_token(expirado=True)

        with pytest.raises(HTTPException) as exc:
            auth_module.decode_token(token, settings)
        assert exc.value.status_code == 401

    def test_rejeita_audience_errada(self, settings):
        token = _make_token(audience="outro-servico")

        with pytest.raises(HTTPException) as exc:
            auth_module.decode_token(token, settings)
        assert exc.value.status_code == 401

    def test_rejeita_assinatura_de_outra_chave(self, settings):
        outra_chave = ec.generate_private_key(ec.SECP256R1())
        agora = datetime.now(timezone.utc)
        token = jwt.encode(
            {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": agora + timedelta(hours=1)},
            outra_chave,
            algorithm="ES256",
        )

        with pytest.raises(HTTPException) as exc:
            auth_module.decode_token(token, settings)
        assert exc.value.status_code == 401

    def test_sem_jwks_url_configurada_falha_como_erro_de_servidor(self):
        settings_sem_jwks = Settings()
        settings_sem_jwks.supabase_jwks_url = ""

        with pytest.raises(HTTPException) as exc:
            auth_module.decode_token(_make_token(), settings_sem_jwks)
        assert exc.value.status_code == 500


class TestGetAuthenticatedClaims:
    def test_sem_credencial_e_401(self, settings):
        with pytest.raises(HTTPException) as exc:
            auth_module.get_authenticated_claims(credentials=None, settings=settings)
        assert exc.value.status_code == 401

    def test_com_token_valido_devolve_claims(self, settings):
        credenciais = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_make_token())

        claims = auth_module.get_authenticated_claims(credentials=credenciais, settings=settings)

        assert "sub" in claims


class TestGetCurrentUser:
    def test_usuario_sem_registro_local_e_403(self, db_engine, settings):
        from app.core.database import SessionLocal

        credenciais = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_make_token())
        db = SessionLocal()
        try:
            with pytest.raises(HTTPException) as exc:
                auth_module.get_current_user(credentials=credenciais, db=db, settings=settings)
            assert exc.value.status_code == 403
        finally:
            db.close()

    def test_usuario_com_registro_local_e_autenticado(self, client, settings, db_engine):
        from app.core.database import SessionLocal
        from app.models.company import Company
        from app.models.users import User

        db = SessionLocal()
        try:
            company = Company(name="Padaria", cnpj="11122233344")
            db.add(company)
            db.flush()

            user_id = uuid.uuid4()
            db.add(
                User(
                    id=user_id,
                    company_id=company.id,
                    name="Dono",
                    email="dono@empresa.com.br",
                    role="owner",
                )
            )
            db.commit()

            token = _make_token(sub=str(user_id))
            credenciais = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            usuario = auth_module.get_current_user(
                credentials=credenciais, db=db, settings=settings
            )

            assert usuario.email == "dono@empresa.com.br"
        finally:
            db.close()
