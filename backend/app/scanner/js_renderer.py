"""Fallback via Playwright para sites que montam a página com JavaScript.

O crawler principal (crawler.py) usa Requests + BeautifulSoup, que não executa
JS — suficiente para a maioria dos sites institucionais de PME, mas cego a
sites em React/Vue/Angular que montam o formulário no client-side. Este módulo
existe só para esse caso, isolado atrás de uma função só (`render_page`), como
o próprio crawler.py já previa desde o início.

Fica separado do crawler principal de propósito: renderizar com um navegador de
verdade é ~10-50x mais lento que um GET simples, então só entra em cena quando
o HTML estático "parece" uma casca de SPA vazia.

Segurança: a URL de entrada passa pelo mesmo filtro de SSRF do crawler estático
(defesa em profundidade — hoje só é chamada com URL já validada por
`_fetch_page_with_js_fallback`, mas a checagem aqui não deve depender disso).
Risco residual e conhecido, não coberto: a página renderizada roda JavaScript de
verdade, que pode fazer suas próprias requisições (fetch/XHR/iframe) para
qualquer endereço, inclusive interno — bloquear isso exigiria interceptar toda
requisição de rede da página (Playwright route interception), o que não está
implementado nesta versão.
"""

import logging

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from app.scanner.ssrf_guard import is_safe_url

logger = logging.getLogger(__name__)

RENDER_TIMEOUT_MS = 15000
USER_AGENT = "LGPDFacilBot/1.0 (+compliance scanner)"


def render_page(url: str) -> tuple[str, list[str]] | None:
    """Abre a URL num Chromium headless, espera o JS rodar e devolve o HTML
    final + nomes dos cookies definidos. None se a renderização falhar.
    """
    if not is_safe_url(url):
        logger.warning("URL recusada pelo filtro de SSRF: %s", url)
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.goto(url, timeout=RENDER_TIMEOUT_MS, wait_until="networkidle")
                html = page.content()
                cookies = [c["name"] for c in context.cookies() if "name" in c]
                return html, cookies
            finally:
                browser.close()
    except PlaywrightError as erro:
        logger.warning("Falha ao renderizar %s com Playwright: %s", url, erro)
        return None
