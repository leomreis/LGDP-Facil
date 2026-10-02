import os

import pytest
from dotenv import load_dotenv

# .env normalmente é carregado por app.core.database, mas isso só acontece
# quando o app é importado — e este arquivo precisa ler TEST_DATABASE_URL antes
# disso, no import do próprio conftest.
load_dotenv()

# Os testes que tocam o banco rodam contra um Postgres descartável, nunca contra o
# Supabase do projeto. A engine é construída no import de app.core.database, então a
# troca de URL precisa acontecer aqui no topo do conftest, antes de qualquer import
# do app (o pytest carrega o conftest antes dos módulos de teste).
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Mesmo raciocínio para a fila: os testes de RQ (test_queue.py, test_enqueue_scan.py,
# test_scan_service.py) usam um banco Redis separado do dev. Sem isso, um worker de
# verdade rodando durante os testes consome os jobs de teste antes do teste conseguir
# inspecionar a fila — foi exatamente o que causou testes falhando durante uma sessão
# de desenvolvimento normal com `python -m app.worker` ativo.
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL")
if TEST_REDIS_URL:
    os.environ["REDIS_URL"] = TEST_REDIS_URL


@pytest.fixture(scope="session")
def db_engine():
    """Cria o schema no banco de teste. Pula a suíte de banco se não houver um."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL não definida — testes de banco pulados")

    from app.core.database import Base, engine

    # Importados só pelo efeito colateral de registrar as tabelas em Base.metadata.
    from app.models.company import Company  # noqa: F401
    from app.models.policy_documents import PolicyDocument  # noqa: F401
    from app.models.reports import Report  # noqa: F401
    from app.models.scan_findings import ScanFinding  # noqa: F401
    from app.models.scans import Scan  # noqa: F401
    from app.models.subscriptions import Subscription  # noqa: F401
    from app.models.users import User  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_engine):
    """TestClient com o banco limpo antes de cada teste, para os testes não se contaminarem."""
    from fastapi.testclient import TestClient

    from app.core.database import Base
    from app.main import app

    with db_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())

    with TestClient(app) as test_client:
        yield test_client


def make_valid_cnpj(seed: int) -> str:
    """CNPJ com dígitos verificadores reais, gerado a partir de `seed` — para
    cada teste poder criar uma empresa com CNPJ único e válido, agora que
    CompanyCreate/OnboardingCreate rejeitam CNPJ com dígito verificador errado.
    """
    from app.core.validators import _calc_digito_verificador

    raiz_e_filial = [int(d) for d in f"{seed % 10**12:012d}"]
    d1 = _calc_digito_verificador(raiz_e_filial, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _calc_digito_verificador(raiz_e_filial + [d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return "".join(str(d) for d in raiz_e_filial + [d1, d2])
