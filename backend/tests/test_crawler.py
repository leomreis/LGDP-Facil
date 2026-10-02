"""Testes do crawler.

Nenhum teste aqui toca a rede: `scan_page` recebe o HTML já baixado, e os testes de
`crawl_site` substituem `fetch_page` por um dicionário de páginas falsas. Scanner que
depende de site de terceiro para o CI passar é scanner que quebra sozinho.
"""

import pytest
from bs4 import BeautifulSoup

from app.models.scan_findings import CategoryType, FindingType, RiskType
from app.scanner import crawler
from app.scanner.crawler import (
    PageResponse,
    crawl_site,
    find_third_party_scripts,
    scan_page,
)

FORMULARIO_HTML = """
<html><body>
  <form action="/contato">
    <label for="nome">Nome completo</label>
    <input type="text" id="nome" name="nome">
    <label for="cpf">CPF</label>
    <input type="text" id="cpf" name="cpf">
    <input type="email" name="contato" placeholder="seu@email.com">
    <textarea name="mensagem"></textarea>
    <input type="submit" value="Enviar">
  </form>
</body></html>
"""


def _categorias(achados, tipo):
    return {a.category for a in achados if a.finding_type is tipo}


class TestScanPage:
    def test_detecta_campos_de_dado_pessoal_do_formulario(self):
        achados = scan_page(PageResponse(html=FORMULARIO_HTML), "https://site.com.br")

        assert _categorias(achados, FindingType.FORM) == {
            CategoryType.full_name,
            CategoryType.cpf,
            CategoryType.email,
        }

    def test_ignora_campo_sem_dado_pessoal(self):
        """O textarea 'mensagem' não coleta dado pessoal identificável."""
        achados = scan_page(PageResponse(html=FORMULARIO_HTML), "https://site.com.br")

        assert all("mensagem" not in a.location for a in achados)

    def test_ignora_botao_de_submit(self):
        achados = scan_page(PageResponse(html=FORMULARIO_HTML), "https://site.com.br")

        assert all("Enviar" not in a.location for a in achados)

    def test_location_aponta_a_url_e_o_campo(self):
        achados = scan_page(PageResponse(html=FORMULARIO_HTML), "https://site.com.br")

        cpf = next(a for a in achados if a.category is CategoryType.cpf)
        assert cpf.location.startswith("https://site.com.br")
        assert "cpf" in cpf.location

    def test_campo_de_cpf_e_risco_alto(self):
        achados = scan_page(PageResponse(html=FORMULARIO_HTML), "https://site.com.br")

        cpf = next(a for a in achados if a.category is CategoryType.cpf)
        assert cpf.risk is RiskType.high

    def test_cookie_de_rastreamento_e_risco_alto(self):
        page = PageResponse(html="<html></html>", cookies=["_ga", "PHPSESSID"])

        achados = scan_page(page, "https://site.com.br")

        riscos = {a.location.split("'")[1]: a.risk for a in achados}
        assert riscos["_ga"] is RiskType.high
        assert riscos["PHPSESSID"] is RiskType.low

    def test_pagina_sem_formulario_nem_cookie_nao_gera_achado(self):
        page = PageResponse(html="<html><body><p>Loja de ferramentas</p></body></html>")

        assert scan_page(page, "https://site.com.br") == []


class TestThirdPartyScripts:
    def test_detecta_script_de_rastreamento_conhecido(self):
        html = """
        <html><body>
          <script src="https://www.googletagmanager.com/gtag/js?id=X"></script>
          <script src="/js/app.js"></script>
          <script src="https://cdn.meucdn.com/lib.js"></script>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        externos = find_third_party_scripts(soup, "https://site.com.br")

        assert len(externos) == 1
        assert "googletagmanager.com" in externos[0]

    def test_script_do_proprio_dominio_nao_e_achado(self):
        html = '<script src="https://site.com.br/js/app.js"></script>'
        soup = BeautifulSoup(html, "html.parser")

        assert find_third_party_scripts(soup, "https://site.com.br") == []


class TestConteudoExposto:
    def test_cpf_impresso_na_pagina_vira_achado(self):
        html = "<html><body><p>Cliente: 529.982.247-25</p></body></html>"

        achados = scan_page(PageResponse(html=html), "https://site.com.br")

        assert CategoryType.cpf in {a.category for a in achados}


class TestCrawlSite:
    @pytest.fixture
    def site_falso(self, monkeypatch):
        paginas = {
            "https://site.com.br": PageResponse(
                html="""
                <html><body>
                  <a href="/contato">Contato</a>
                  <a href="https://externo.com/x">Externo</a>
                </body></html>
                """
            ),
            "https://site.com.br/contato": PageResponse(html=FORMULARIO_HTML),
        }
        monkeypatch.setattr(crawler, "fetch_page", lambda url: paginas.get(url))
        return paginas

    def test_segue_links_internos_e_acha_o_formulario_na_pagina_interna(self, site_falso):
        resultado = crawl_site("https://site.com.br")

        assert resultado.pages_visited == [
            "https://site.com.br",
            "https://site.com.br/contato",
        ]
        assert CategoryType.cpf in {a.category for a in resultado.findings}

    def test_nao_sai_do_dominio(self, site_falso):
        resultado = crawl_site("https://site.com.br")

        assert all("externo.com" not in url for url in resultado.pages_visited)

    def test_respeita_o_limite_de_paginas(self, site_falso):
        resultado = crawl_site("https://site.com.br", max_pages=1)

        assert len(resultado.pages_visited) == 1

    def test_pagina_ilegivel_vira_erro_e_nao_derruba_o_scan(self, monkeypatch):
        monkeypatch.setattr(crawler, "fetch_page", lambda url: None)

        resultado = crawl_site("https://site-fora-do-ar.com.br")

        assert resultado.findings == []
        assert len(resultado.errors) == 1

    def test_achado_repetido_em_varias_paginas_conta_uma_vez(self, monkeypatch):
        rodape = '<html><body><form><input name="email"></form></body></html>'
        paginas = {
            "https://site.com.br": PageResponse(
                html=rodape.replace("</form>", '</form><a href="/sobre">Sobre</a>')
            ),
            "https://site.com.br/sobre": PageResponse(html=rodape),
        }
        monkeypatch.setattr(crawler, "fetch_page", lambda url: paginas.get(url))

        resultado = crawl_site("https://site.com.br")

        emails = [a for a in resultado.findings if a.category is CategoryType.email]
        assert len(resultado.pages_visited) == 2  # o campo apareceu nas duas páginas
        assert len(emails) == 1  # mas é um problema de compliance só
        assert emails[0].page_url == "https://site.com.br"  # registra onde foi visto 1º


class TestLooksLikeSpaShell:
    def test_casca_vazia_de_spa_e_reconhecida(self):
        html = '<html><body><div id="root"></div></body></html>'

        assert crawler._looks_like_spa_shell(html) is True

    def test_pagina_com_texto_suficiente_nao_e_casca(self):
        html = f"<html><body><p>{'Conteúdo real da página. ' * 20}</p></body></html>"

        assert crawler._looks_like_spa_shell(html) is False

    def test_pagina_curta_mas_com_formulario_nao_e_casca(self):
        """Um formulário de contato minimalista não deve ser confundido com SPA vazia."""
        html = '<html><body><form><input name="email"></form></body></html>'

        assert crawler._looks_like_spa_shell(html) is False


class TestFetchPageWithJsFallback:
    def test_pagina_estatica_com_conteudo_nao_aciona_o_fallback(self, monkeypatch):
        monkeypatch.setattr(crawler, "fetch_page", lambda url: PageResponse(html=FORMULARIO_HTML))
        chamou_render = []
        monkeypatch.setattr(crawler, "render_page", lambda url: chamou_render.append(url) or None)

        pagina = crawler._fetch_page_with_js_fallback("https://site.com.br")

        assert pagina.html == FORMULARIO_HTML
        assert chamou_render == []

    def test_casca_de_spa_aciona_o_fallback_e_usa_o_html_renderizado(self, monkeypatch):
        casca = '<html><body><div id="root"></div></body></html>'
        html_renderizado = '<html><body><form><input name="cpf"></form></body></html>'
        monkeypatch.setattr(crawler, "fetch_page", lambda url: PageResponse(html=casca))
        monkeypatch.setattr(crawler, "render_page", lambda url: (html_renderizado, ["session_id"]))

        pagina = crawler._fetch_page_with_js_fallback("https://spa.com.br")

        assert pagina.html == html_renderizado
        assert pagina.cookies == ["session_id"]

    def test_fallback_falha_mantem_a_casca_estatica(self, monkeypatch):
        """Sem Chromium disponível ou renderização falha: melhor uma casca vazia
        do que nenhum resultado — o scan continua em vez de abortar a página."""
        casca = '<html><body><div id="root"></div></body></html>'
        monkeypatch.setattr(crawler, "fetch_page", lambda url: PageResponse(html=casca))
        monkeypatch.setattr(crawler, "render_page", lambda url: None)

        pagina = crawler._fetch_page_with_js_fallback("https://spa-fora-do-ar.com.br")

        assert pagina.html == casca

    def test_pagina_totalmente_inacessivel_nao_aciona_o_fallback(self, monkeypatch):
        """fetch_page falhando (timeout/DNS) não tenta o navegador — se nem um GET
        simples responde, tentar renderizar só deixaria o scan mais lento à toa."""
        monkeypatch.setattr(crawler, "fetch_page", lambda url: None)
        chamou_render = []
        monkeypatch.setattr(crawler, "render_page", lambda url: chamou_render.append(url) or None)

        pagina = crawler._fetch_page_with_js_fallback("https://fora-do-ar.com.br")

        assert pagina is None
        assert chamou_render == []


class TestCrawlSiteComSpa:
    def test_crawl_site_usa_o_fallback_de_js_quando_necessario(self, monkeypatch):
        casca = '<html><body><div id="root"></div></body></html>'
        html_renderizado = '<html><body><form><input name="cpf"></form></body></html>'
        monkeypatch.setattr(crawler, "fetch_page", lambda url: PageResponse(html=casca))
        monkeypatch.setattr(crawler, "render_page", lambda url: (html_renderizado, []))

        resultado = crawl_site("https://spa.com.br")

        assert CategoryType.cpf in {a.category for a in resultado.findings}


class TestFetchPageSSRFDefense:
    def test_url_insegura_e_bloqueada_sem_fazer_nenhuma_requisicao(self, monkeypatch):
        chamadas = []
        monkeypatch.setattr(crawler.requests, "get", lambda *a, **k: chamadas.append(a) or None)

        pagina = crawler.fetch_page("http://169.254.169.254/latest/meta-data/")

        assert pagina is None
        assert chamadas == []

    def test_busca_uma_url_publica_real(self):
        """Único teste do arquivo que toca a rede de verdade — prova que a defesa
        de SSRF não quebrou o caminho normal (site público de verdade)."""
        pagina = crawler.fetch_page("https://example.com")

        assert pagina is not None
        assert "<html" in pagina.html.lower()

    def test_redirect_para_ip_privado_e_bloqueado_no_meio_da_cadeia(self, monkeypatch):
        """SSRF pelo caminho indireto: uma URL pública que redireciona para um IP
        interno. Sem revalidar cada salto, `allow_redirects=True` já teria
        buscado o destino antes de qualquer chance de bloquear."""

        class RespostaFalsaRedirect:
            is_redirect = True
            status_code = 302
            headers = {"Location": "http://127.0.0.1:8000/segredo"}
            cookies = type("C", (), {"get_dict": lambda self: {}})()

            def close(self):
                pass

        chamadas = []

        def get_falso(url, **kwargs):
            chamadas.append(url)
            return RespostaFalsaRedirect()

        monkeypatch.setattr(crawler.requests, "get", get_falso)

        pagina = crawler.fetch_page(
            "https://example.com"
        )  # domínio público real, resolve de verdade

        assert pagina is None
        # A primeira chamada é feita (URL pública, segura); a segunda (o destino
        # do redirect, um IP privado) nunca chega a acontecer.
        assert len(chamadas) == 1

    def test_resposta_maior_que_o_limite_e_recusada(self, monkeypatch):
        class RespostaFalsaGrande:
            is_redirect = False
            status_code = 200
            headers = {"Content-Type": "text/html"}
            encoding = "utf-8"
            cookies = type("C", (), {"get_dict": lambda self: {}})()

            def iter_content(self, chunk_size):
                pedaco_grande = b"a" * (1024 * 1024)
                for _ in range(10):  # 10 MB > MAX_RESPONSE_BYTES (5 MB)
                    yield pedaco_grande

            def close(self):
                pass

        monkeypatch.setattr(crawler.requests, "get", lambda url, **k: RespostaFalsaGrande())

        pagina = crawler.fetch_page("https://example.com")

        assert pagina is None
