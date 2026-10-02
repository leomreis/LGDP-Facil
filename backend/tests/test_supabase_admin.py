"""Testes de construção de requisição/parsing de resposta. Nunca chamam a
Supabase Admin API real — isso enviaria um e-mail de convite de verdade."""

import pytest

from app.core.config import Settings
from app.services.supabase_admin import SupabaseAdminError, invite_user


def _settings_com_credenciais():
    settings = Settings()
    settings.supabase_url = "https://projeto-fake.supabase.co"
    settings.supabase_secret_key = "sb_secret_fake"
    return settings


class RespostaFalsa:
    def __init__(self, status_code, corpo, texto=""):
        self.status_code = status_code
        self._corpo = corpo
        self.text = texto or str(corpo)

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._corpo


class TestInviteUser:
    def test_sem_credenciais_configuradas_falha_direto_sem_chamar_a_rede(self, monkeypatch):
        chamou = []
        monkeypatch.setattr("requests.post", lambda *a, **k: chamou.append(a) or None)
        settings = Settings()
        settings.supabase_url = ""
        settings.supabase_secret_key = ""

        with pytest.raises(SupabaseAdminError, match="SUPABASE_URL"):
            invite_user("novo@empresa.com", settings)
        assert chamou == []

    def test_sucesso_devolve_o_id_do_usuario_criado(self, monkeypatch):
        monkeypatch.setattr(
            "requests.post",
            lambda *a, **k: RespostaFalsa(200, {"id": "abc-123", "email": "novo@empresa.com"}),
        )

        user_id = invite_user("novo@empresa.com", _settings_com_credenciais())

        assert user_id == "abc-123"

    def test_email_ja_cadastrado_vira_erro_claro(self, monkeypatch):
        monkeypatch.setattr(
            "requests.post",
            lambda *a, **k: RespostaFalsa(422, {"msg": "User already registered"}),
        )

        with pytest.raises(SupabaseAdminError, match="já cadastrado"):
            invite_user("existente@empresa.com", _settings_com_credenciais())

    def test_erro_5xx_da_supabase_vira_supabase_admin_error(self, monkeypatch):
        monkeypatch.setattr(
            "requests.post", lambda *a, **k: RespostaFalsa(500, {}, texto="erro interno")
        )

        with pytest.raises(SupabaseAdminError):
            invite_user("novo@empresa.com", _settings_com_credenciais())

    def test_resposta_sem_id_vira_erro(self, monkeypatch):
        monkeypatch.setattr("requests.post", lambda *a, **k: RespostaFalsa(200, {"foo": "bar"}))

        with pytest.raises(SupabaseAdminError, match="inesperada"):
            invite_user("novo@empresa.com", _settings_com_credenciais())

    def test_envia_a_service_role_key_como_apikey_e_bearer(self, monkeypatch):
        chamadas = []

        def post_falso(url, headers, json, timeout):
            chamadas.append((url, headers, json))
            return RespostaFalsa(200, {"id": "xyz"})

        monkeypatch.setattr("requests.post", post_falso)
        settings = _settings_com_credenciais()

        invite_user("novo@empresa.com", settings)

        url, headers, corpo = chamadas[0]
        assert url == "https://projeto-fake.supabase.co/auth/v1/invite"
        assert headers["apikey"] == "sb_secret_fake"
        assert headers["Authorization"] == "Bearer sb_secret_fake"
        assert corpo == {"email": "novo@empresa.com"}
