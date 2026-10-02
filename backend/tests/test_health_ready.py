def test_health_devolve_ok_sempre_sem_checar_dependencias(client):
    """Liveness não deve depender de banco/redis estarem acessíveis."""
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_health_ready_devolve_ok_quando_banco_esta_acessivel(client, db_engine):
    resposta = client.get("/health/ready")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_health_ready_devolve_503_quando_banco_falha(client, db_engine, monkeypatch):
    from app.core.database import get_db
    from app.main import app

    def get_db_quebrado():
        class SessaoQuebrada:
            def execute(self, *a, **k):
                raise RuntimeError("conexão recusada")

        yield SessaoQuebrada()

    app.dependency_overrides[get_db] = get_db_quebrado
    try:
        resposta = client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resposta.status_code == 503
    assert "database" in resposta.json()["problemas"]
