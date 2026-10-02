"""Testes de integração de /team. `invite_user` é sempre mockado — a Supabase
Admin API real nunca é chamada por um teste (enviaria e-mail de verdade)."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.api import team as team_module
from app.core import auth as auth_module
from app.services.supabase_admin import SupabaseAdminError
from tests.conftest import make_valid_cnpj

PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_KEY = PRIVATE_KEY.public_key()


class JWKSClientFalso:
    def get_signing_key_from_jwt(self, token: str):
        class SigningKeyFalsa:
            key = PUBLIC_KEY

        return SigningKeyFalsa()


def _make_token(email):
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": email,
        "aud": "authenticated",
        "exp": agora + timedelta(hours=1),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="ES256")


def _onboard(client, monkeypatch, email="dono@empresa.com.br"):
    monkeypatch.setattr(auth_module, "_jwks_client", lambda url: JWKSClientFalso())
    token = _make_token(email)
    client.post(
        "/onboarding",
        json={
            "company_name": "Padaria",
            "cnpj": make_valid_cnpj(uuid.uuid4().int),
            "user_name": "Dono",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {token}"}


class TestInviteTeamMember:
    def test_owner_convida_com_sucesso(self, client, monkeypatch, db_engine):
        headers = _onboard(client, monkeypatch)
        monkeypatch.setattr(team_module, "invite_user", lambda email, settings: str(uuid.uuid4()))

        resposta = client.post(
            "/team/invitations",
            json={"email": "novo@empresa.com.br", "name": "Novo Membro"},
            headers=headers,
        )

        assert resposta.status_code == 201
        body = resposta.json()
        assert body["email"] == "novo@empresa.com.br"
        assert body["role"] == "member"

    def test_membro_convidado_aparece_na_listagem_da_mesma_empresa(
        self, client, monkeypatch, db_engine
    ):
        headers = _onboard(client, monkeypatch)
        monkeypatch.setattr(team_module, "invite_user", lambda email, settings: str(uuid.uuid4()))

        client.post(
            "/team/invitations",
            json={"email": "novo@empresa.com.br", "name": "Novo Membro"},
            headers=headers,
        )
        resposta = client.get("/team/members", headers=headers)

        assert resposta.status_code == 200
        emails = {m["email"] for m in resposta.json()}
        assert "novo@empresa.com.br" in emails
        assert len(resposta.json()) == 2  # dono + convidado

    def test_membro_nao_owner_nao_pode_convidar(self, client, monkeypatch, db_engine):
        """Só quem fez o onboarding (role=owner) pode convidar; um segundo
        membro (role=member) não pode ampliar o acesso à empresa sozinho."""
        headers = _onboard(client, monkeypatch)
        monkeypatch.setattr(team_module, "invite_user", lambda email, settings: str(uuid.uuid4()))
        client.post(
            "/team/invitations",
            json={"email": "membro@empresa.com.br", "name": "Membro"},
            headers=headers,
        )

        # loga como o membro recém-convidado (mesmo sub que o invite_user mockado não usa
        # diretamente — simulamos pegando um token novo para esse e-mail/sub não teria
        # o id certo; em vez disso, forçamos o cenário via nova empresa+membro direto)
        from app.core.database import SessionLocal
        from app.models.users import User

        db = SessionLocal()
        try:
            membro = db.query(User).filter(User.email == "membro@empresa.com.br").first()
            assert membro is not None, "convite ao membro falhou — checar _onboard/cnpj"
            membro_id = membro.id
        finally:
            db.close()

        token_membro = jwt.encode(
            {
                "sub": str(membro_id),
                "email": "membro@empresa.com.br",
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            PRIVATE_KEY,
            algorithm="ES256",
        )

        resposta = client.post(
            "/team/invitations",
            json={"email": "outro@empresa.com.br", "name": "Outro"},
            headers={"Authorization": f"Bearer {token_membro}"},
        )

        assert resposta.status_code == 403

    def test_convidar_email_ja_cadastrado_na_empresa_e_409(self, client, monkeypatch, db_engine):
        headers = _onboard(client, monkeypatch, email="dono2@empresa.com.br")
        monkeypatch.setattr(team_module, "invite_user", lambda email, settings: str(uuid.uuid4()))

        client.post(
            "/team/invitations",
            json={"email": "repetido@empresa.com.br", "name": "X"},
            headers=headers,
        )
        resposta = client.post(
            "/team/invitations",
            json={"email": "repetido@empresa.com.br", "name": "X de novo"},
            headers=headers,
        )

        assert resposta.status_code == 409

    def test_falha_na_supabase_admin_api_vira_502(self, client, monkeypatch, db_engine):
        headers = _onboard(client, monkeypatch, email="dono3@empresa.com.br")

        def invite_que_falha(email, settings):
            raise SupabaseAdminError("fora do ar")

        monkeypatch.setattr(team_module, "invite_user", invite_que_falha)

        resposta = client.post(
            "/team/invitations",
            json={"email": "novo@empresa.com.br", "name": "X"},
            headers=headers,
        )

        assert resposta.status_code == 502


class TestRemoveTeamMember:
    def test_owner_remove_membro_com_sucesso(self, client, monkeypatch, db_engine):
        headers = _onboard(client, monkeypatch, email="dono4@empresa.com.br")
        monkeypatch.setattr(team_module, "invite_user", lambda email, settings: str(uuid.uuid4()))
        convite = client.post(
            "/team/invitations",
            json={"email": "removivel@empresa.com.br", "name": "X"},
            headers=headers,
        )
        membro_id = convite.json()["id"]

        resposta = client.delete(f"/team/members/{membro_id}", headers=headers)

        assert resposta.status_code == 204
        membros = client.get("/team/members", headers=headers).json()
        assert all(m["id"] != membro_id for m in membros)

    def test_nao_owner_nao_pode_remover(self, client, monkeypatch, db_engine):
        headers = _onboard(client, monkeypatch, email="dono5@empresa.com.br")
        monkeypatch.setattr(team_module, "invite_user", lambda email, settings: str(uuid.uuid4()))
        convite = client.post(
            "/team/invitations",
            json={"email": "membro5@empresa.com.br", "name": "M"},
            headers=headers,
        )
        membro_id = convite.json()["id"]

        token_membro = jwt.encode(
            {
                "sub": membro_id,
                "email": "membro5@empresa.com.br",
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            PRIVATE_KEY,
            algorithm="ES256",
        )

        resposta = client.delete(
            f"/team/members/{membro_id}",
            headers={"Authorization": f"Bearer {token_membro}"},
        )

        assert resposta.status_code == 403

    def test_unico_owner_nao_pode_se_remover(self, client, monkeypatch, db_engine):
        """Caso particular da regra real: remover deixaria a empresa sem
        nenhum owner. Não é uma checagem de "não remova a si mesmo" — é a
        mesma regra que se aplicaria a qualquer remoção nessas condições."""
        headers = _onboard(client, monkeypatch, email="dono6@empresa.com.br")
        euMesmo = client.get("/users/me", headers=headers).json()

        resposta = client.delete(f"/team/members/{euMesmo['id']}", headers=headers)

        assert resposta.status_code == 400

    def test_remover_membro_inexistente_e_404(self, client, monkeypatch, db_engine):
        headers = _onboard(client, monkeypatch, email="dono7@empresa.com.br")

        resposta = client.delete(f"/team/members/{uuid.uuid4()}", headers=headers)

        assert resposta.status_code == 404

    def test_owner_pode_se_remover_quando_existe_outro_owner(self, client, monkeypatch, db_engine):
        """Com outro owner na empresa, sair não deixa a empresa sem dono —
        deve ser permitido, mesmo sendo uma auto-remoção."""
        headers = _onboard(client, monkeypatch, email="dono8@empresa.com.br")
        euMesmo = client.get("/users/me", headers=headers).json()

        from app.core.database import SessionLocal
        from app.models.users import User

        db = SessionLocal()
        try:
            outro_owner = User(
                id=uuid.uuid4(),
                company_id=euMesmo["company_id"],
                name="Segundo Dono",
                email="dono8b@empresa.com.br",
                role="owner",
            )
            db.add(outro_owner)
            db.commit()
        finally:
            db.close()

        resposta = client.delete(f"/team/members/{euMesmo['id']}", headers=headers)

        assert resposta.status_code == 204

    def test_um_de_dois_owners_pode_remover_o_outro(self, client, monkeypatch, db_engine):
        headers = _onboard(client, monkeypatch, email="dono9@empresa.com.br")
        euMesmo = client.get("/users/me", headers=headers).json()

        from app.core.database import SessionLocal
        from app.models.users import User

        db = SessionLocal()
        try:
            outro_owner = User(
                id=uuid.uuid4(),
                company_id=euMesmo["company_id"],
                name="Segundo Dono",
                email="dono9b@empresa.com.br",
                role="owner",
            )
            db.add(outro_owner)
            db.commit()
            outro_owner_id = outro_owner.id
        finally:
            db.close()

        token_outro_owner = jwt.encode(
            {
                "sub": str(outro_owner_id),
                "email": "dono9b@empresa.com.br",
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            PRIVATE_KEY,
            algorithm="ES256",
        )

        resposta = client.delete(
            f"/team/members/{euMesmo['id']}",
            headers={"Authorization": f"Bearer {token_outro_owner}"},
        )

        assert resposta.status_code == 204
