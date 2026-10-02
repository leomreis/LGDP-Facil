"""Testes contra um Chromium headless real (instalado via `playwright install
chromium`). Usam `data:` URLs — sem tocar a rede — para o teste ser rápido e
determinístico mesmo usando o navegador de verdade. Pulados se o binário do
Chromium não estiver instalado nesta máquina."""

import pytest

from app.scanner.js_renderer import render_page


def _chromium_disponivel() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False


# skipif abaixo só protege os testes que precisam do navegador de verdade
_skip_sem_chromium = pytest.mark.skipif(
    not _chromium_disponivel(),
    reason="Chromium do Playwright não instalado — rode `playwright install chromium`",
)


@_skip_sem_chromium
def test_render_page_executa_dom_montado_por_javascript():
    """O ponto inteiro deste módulo: HTML que só existe depois do JS rodar."""
    url = (
        "data:text/html,"
        "<html><body><div id='root'></div>"
        "<script>document.getElementById('root').innerHTML="
        "'<form><input name=\"cpf\"></form>';</script>"
        "</body></html>"
    )

    resultado = render_page(url)

    assert resultado is not None
    html, _cookies = resultado
    assert "<form>" in html
    assert 'name="cpf"' in html


@_skip_sem_chromium
def test_render_page_devolve_cookies_como_lista_de_nomes():
    resultado = render_page("data:text/html,<html><body>ok</body></html>")

    assert resultado is not None
    _html, cookies = resultado
    assert isinstance(cookies, list)


@_skip_sem_chromium
def test_render_page_url_invalida_devolve_none():
    resultado = render_page("not-a-valid-url")

    assert resultado is None


# Este teste não depende de Chromium instalado: a URL é recusada pelo filtro
# de SSRF antes de qualquer tentativa de abrir o navegador.
def test_render_page_recusa_ip_interno_sem_abrir_o_navegador():
    resultado = render_page("http://169.254.169.254/latest/meta-data/")

    assert resultado is None
