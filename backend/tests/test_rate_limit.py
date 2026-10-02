import uuid

import pytest
from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.core.rate_limit import check_rate_limit


class TestModoMemoria:
    def test_permite_ate_o_limite_e_bloqueia_a_seguir(self):
        settings = Settings()
        settings.redis_url = ""
        key = f"teste:{uuid.uuid4()}"

        for _ in range(3):
            check_rate_limit(key, max_calls=3, window_seconds=60, settings=settings)

        with pytest.raises(Exception) as exc:
            check_rate_limit(key, max_calls=3, window_seconds=60, settings=settings)
        assert exc.value.status_code == 429

    def test_chaves_diferentes_nao_interferem_entre_si(self):
        settings = Settings()
        settings.redis_url = ""

        chave_a = f"teste:{uuid.uuid4()}"
        chave_b = f"teste:{uuid.uuid4()}"

        for _ in range(3):
            check_rate_limit(chave_a, max_calls=3, window_seconds=60, settings=settings)

        # chave_b não foi tocada — deve aceitar normalmente, mesmo com chave_a no limite.
        check_rate_limit(chave_b, max_calls=3, window_seconds=60, settings=settings)

    def test_janela_expirada_libera_novas_chamadas(self, monkeypatch):
        import app.core.rate_limit as rl

        settings = Settings()
        settings.redis_url = ""
        key = f"teste:{uuid.uuid4()}"
        agora = [1000.0]
        monkeypatch.setattr(rl.time, "monotonic", lambda: agora[0])

        check_rate_limit(key, max_calls=1, window_seconds=10, settings=settings)
        with pytest.raises(HTTPException):
            check_rate_limit(key, max_calls=1, window_seconds=10, settings=settings)

        agora[0] += 11  # passou da janela de 10s
        # não deve levantar: a janela anterior expirou
        check_rate_limit(key, max_calls=1, window_seconds=10, settings=settings)


class TestModoRedis:
    @pytest.fixture(autouse=True)
    def redis_disponivel(self):
        if not get_settings().redis_url:
            pytest.skip("REDIS_URL não configurada — teste pulado")

    def test_permite_ate_o_limite_e_bloqueia_a_seguir(self):
        from app.core.queue import get_redis_connection

        settings = get_settings()
        key = f"teste:{uuid.uuid4()}"

        for _ in range(3):
            check_rate_limit(key, max_calls=3, window_seconds=60, settings=settings)

        with pytest.raises(Exception) as exc:
            check_rate_limit(key, max_calls=3, window_seconds=60, settings=settings)
        assert exc.value.status_code == 429

        get_redis_connection().delete(f"ratelimit:{key}")
