import uuid

from tests.conftest import make_valid_cnpj


def test_create_company_persiste_e_devolve_a_empresa(client):
    payload = {
        "name": "Padaria do Bairro LTDA",
        "cnpj": make_valid_cnpj(1),
        "site_url": "https://padariadobairro.com.br",
    }

    response = client.post("/companies", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == payload["name"]
    assert body["cnpj"] == payload["cnpj"]
    assert body["site_url"] == payload["site_url"]
    # Campos gerados pelo banco: precisam voltar preenchidos e no formato certo.
    assert uuid.UUID(body["id"])
    assert body["created_at"] is not None


def test_create_company_aceita_software_name_sem_site(client):
    """PMEs que vendem software, e não site, informam software_name no lugar de site_url."""
    payload = {
        "name": "Oficina de Software ME",
        "cnpj": make_valid_cnpj(2),
        "software_name": "GestorPro",
    }

    response = client.post("/companies", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["software_name"] == "GestorPro"
    assert body["site_url"] is None


def test_create_company_exige_cnpj(client):
    response = client.post("/companies", json={"name": "Empresa Sem CNPJ"})

    assert response.status_code == 422
    campos_com_erro = {erro["loc"][-1] for erro in response.json()["detail"]}
    assert "cnpj" in campos_com_erro


def test_create_company_rejeita_cnpj_com_digito_verificador_errado(client):
    payload = {"name": "Empresa X", "cnpj": "11222333000180"}  # último dígito errado

    response = client.post("/companies", json=payload)

    assert response.status_code == 422
