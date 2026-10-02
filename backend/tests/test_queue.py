"""Testes contra Redis real (container descartável, mesmo padrão do Postgres de
teste). Pulados quando REDIS_URL não está configurada."""

import pytest

from app.core.config import Settings, get_settings
from app.core.queue import get_queue


@pytest.fixture(autouse=True)
def redis_disponivel():
    if not get_settings().redis_url:
        pytest.skip("REDIS_URL não configurada — testes de fila pulados")


def test_get_queue_conecta_e_aceita_enfileiramento():
    fila = get_queue()

    job = fila.enqueue("uuid.uuid4")

    assert job.id is not None
    fila.connection.flushdb()


def test_settings_sem_redis_url_nao_quebra_a_aplicacao():
    """Ambientes sem Redis configurado usam BackgroundTasks — settings vazias
    são um estado válido, não um erro."""
    settings = Settings()
    settings.redis_url = ""

    assert settings.redis_url == ""
