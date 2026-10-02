def test_resposta_normal_tem_os_cabecalhos_de_seguranca(client):
    resposta = client.get("/health")

    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.headers["x-frame-options"] == "DENY"
    assert resposta.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "max-age=" in resposta.headers["strict-transport-security"]
    csp_esperado = "default-src 'none'; frame-ancestors 'none'"
    assert resposta.headers["content-security-policy"] == csp_esperado


def test_docs_nao_recebe_csp_para_nao_quebrar_o_swagger(client):
    resposta = client.get("/docs")

    assert "content-security-policy" not in resposta.headers
    # os outros cabeçalhos continuam presentes normalmente
    assert resposta.headers["x-content-type-options"] == "nosniff"
