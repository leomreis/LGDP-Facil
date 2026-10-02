from app.core.config import Settings
from app.core.observability import init_sentry


def test_sem_dsn_nao_chama_sentry_sdk_init(monkeypatch):
    """Sem SENTRY_DSN, o projeto roda sem nenhuma conta no Sentry, como hoje —
    init_sentry precisa ser um no-op silencioso, nunca levantar exceção."""
    import sentry_sdk

    chamadas = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: chamadas.append(kwargs))

    settings = Settings()
    settings.sentry_dsn = ""

    init_sentry(settings)

    assert chamadas == []


def test_com_dsn_chama_sentry_sdk_init(monkeypatch):
    import sentry_sdk

    chamadas = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: chamadas.append(kwargs))

    settings = Settings()
    settings.sentry_dsn = "https://fake@sentry.example/1"
    settings.environment = "test"

    init_sentry(settings)

    assert len(chamadas) == 1
    assert chamadas[0]["dsn"] == "https://fake@sentry.example/1"
    assert chamadas[0]["environment"] == "test"
