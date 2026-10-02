"""Crawler: varre páginas públicas com Requests + BeautifulSoup, com fallback
para Playwright em sites que montam o conteúdo via JavaScript.

A varredura padrão usa Requests (rápido, sem navegador). Quando o HTML estático
parece uma casca vazia de SPA (`_looks_like_spa_shell`), a página é renderizada
de novo com um Chromium headless (js_renderer.py) antes de desistir dela.
"""

import logging
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.models.scan_findings import CategoryType, FindingType, RiskType
from app.scanner.js_renderer import render_page
from app.scanner.ssrf_guard import is_safe_url
from app.services.personal_data_classifier import FormField, classify_field, detect_in_text

logger = logging.getLogger(__name__)

USER_AGENT = "LGPDFacilBot/1.0 (+compliance scanner)"
REQUEST_TIMEOUT_SECONDS = 10
MAX_PAGES = 20
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB — página HTML legítima não passa disso
MAX_REDIRECTS = 5

# Cookies próprios de sessão não são achado; o que interessa para a LGPD é
# rastreamento de terceiros.
THIRD_PARTY_SCRIPT_HOSTS = (
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "facebook.net",
    "facebook.com",
    "hotjar.com",
    "clarity.ms",
    "tiktok.com",
    "linkedin.com",
    "twitter.com",
    "adservice.google.com",
)


@dataclass
class RawFinding:
    """Achado bruto, no formato que vira uma linha de scan_findings.

    `page_url` e `detail` ficam separados porque a deduplicação usa só o detalhe:
    o mesmo campo de newsletter no rodapé de 20 páginas é um problema de
    compliance, não vinte.
    """

    finding_type: FindingType
    category: CategoryType
    risk: RiskType
    page_url: str
    detail: str

    @property
    def location(self) -> str:
        return f"{self.page_url} > {self.detail}"


@dataclass
class PageResponse:
    """HTML e cookies de uma página — os cookies só existem na resposta HTTP."""

    html: str
    cookies: list[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    findings: list[RawFinding] = field(default_factory=list)
    pages_visited: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def fetch_page(url: str) -> PageResponse | None:
    """Baixa uma página. Devolve None quando a página não é utilizável ou não é
    segura de buscar (ver ssrf_guard.py).

    Redirects são seguidos manualmente, um de cada vez, revalidando o destino a
    cada salto — `requests` com `allow_redirects=True` buscaria o destino do
    redirect *antes* de qualquer chance de bloqueá-lo, o que reabriria o SSRF
    por um caminho indireto (ex.: URL pública que redireciona para 127.0.0.1).
    """
    proxima_url = url
    cookies_acumulados: dict[str, str] = {}

    for _salto in range(MAX_REDIRECTS + 1):
        if not is_safe_url(proxima_url):
            logger.warning("URL recusada pelo filtro de SSRF: %s", proxima_url)
            return None

        try:
            response = requests.get(
                proxima_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as erro:
            logger.warning("Falha ao baixar %s: %s", proxima_url, erro)
            return None

        cookies_acumulados.update(
            {k: v for k, v in response.cookies.get_dict().items() if v is not None}
        )

        if response.is_redirect:
            destino = response.headers.get("Location")
            response.close()
            if not destino:
                return None
            proxima_url = urljoin(proxima_url, destino)
            continue

        try:
            if response.status_code >= 400:
                return None
            if "html" not in response.headers.get("Content-Type", ""):
                return None

            corpo = _read_capped(response)
            if corpo is None:
                logger.warning("Resposta de %s excede o limite de tamanho", proxima_url)
                return None

            return PageResponse(html=corpo, cookies=list(cookies_acumulados.keys()))
        finally:
            response.close()

    logger.warning("Excedeu %s redirects ao buscar %s", MAX_REDIRECTS, url)
    return None


def _read_capped(response: requests.Response) -> str | None:
    """Lê o corpo da resposta até MAX_RESPONSE_BYTES. None se ultrapassar —
    protege contra uma resposta gigante (deliberada ou não) esgotar memória."""
    total = 0
    pedacos: list[bytes] = []
    for pedaco in response.iter_content(chunk_size=64 * 1024):
        total += len(pedaco)
        if total > MAX_RESPONSE_BYTES:
            return None
        pedacos.append(pedaco)
    return b"".join(pedacos).decode(response.encoding or "utf-8", errors="replace")


def _attr(tag, nome: str) -> str:
    """Lê um atributo HTML como string.

    O BeautifulSoup tipa atributos como `str | list[str] | None`, porque atributos
    multivalorados (class) viram lista. Aqui só interessam atributos simples.
    """
    valor = tag.get(nome)
    if isinstance(valor, list):
        return " ".join(valor)
    return valor or ""


def _same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def _extract_internal_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        destino = urljoin(base_url, _attr(anchor, "href")).split("#")[0]
        if _same_domain(destino, base_url) and destino not in links:
            links.append(destino)
    return links


def _label_for(soup: BeautifulSoup, input_tag) -> str:
    """Procura o <label> associado ao input — é onde o rótulo humano costuma estar."""
    input_id = _attr(input_tag, "id")
    if input_id:
        label = soup.find("label", attrs={"for": input_id})
        if label:
            return label.get_text(strip=True)

    label_ancestral = input_tag.find_parent("label")
    return label_ancestral.get_text(strip=True) if label_ancestral else ""


def find_form_fields(soup: BeautifulSoup) -> list[FormField]:
    campos: list[FormField] = []
    for form in soup.find_all("form"):
        for tag in form.find_all(["input", "textarea", "select"]):
            if tag.get("type") in ("submit", "button", "hidden", "checkbox", "radio"):
                continue
            campos.append(
                FormField(
                    name=_attr(tag, "name") or _attr(tag, "id"),
                    input_type=_attr(tag, "type"),
                    label=_label_for(soup, tag),
                    placeholder=_attr(tag, "placeholder"),
                )
            )
    return campos


def find_third_party_scripts(soup: BeautifulSoup, base_url: str) -> list[str]:
    externos: list[str] = []
    for script in soup.find_all("script", src=True):
        src = urljoin(base_url, _attr(script, "src"))
        if _same_domain(src, base_url):
            continue
        if any(host in urlparse(src).netloc for host in THIRD_PARTY_SCRIPT_HOSTS):
            externos.append(src)
    return externos


def _cookie_risk(nome_cookie: str) -> RiskType:
    """Cookie de rastreamento exige consentimento; cookie de sessão próprio, não."""
    conhecido_de_rastreio = ("_ga", "_gid", "_fbp", "_fbc", "_gcl", "_hj", "utm")
    nome = nome_cookie.lower()
    return (
        RiskType.high
        if any(nome.startswith(prefixo) for prefixo in conhecido_de_rastreio)
        else RiskType.low
    )


def scan_page(page: PageResponse, url: str) -> list[RawFinding]:
    """Extrai todos os achados de uma única página já baixada."""
    soup = BeautifulSoup(page.html, "html.parser")
    achados: list[RawFinding] = []

    for cookie in page.cookies:
        achados.append(
            RawFinding(
                finding_type=FindingType.COOKIES,
                category=CategoryType.other,
                risk=_cookie_risk(cookie),
                page_url=url,
                detail=f"cookie '{cookie}'",
            )
        )

    for campo in find_form_fields(soup):
        classificacao = classify_field(campo)
        if classificacao.category is CategoryType.other:
            continue  # campo sem dado pessoal (assunto, mensagem) não vira achado
        identificacao = campo.name or campo.label or campo.placeholder
        achados.append(
            RawFinding(
                finding_type=FindingType.FORM,
                category=classificacao.category,
                risk=classificacao.risk,
                page_url=url,
                detail=f"formulário > campo '{identificacao}'",
            )
        )

    for src in find_third_party_scripts(soup, url):
        achados.append(
            RawFinding(
                finding_type=FindingType.THIRD_PARTY_SCRIPT,
                category=CategoryType.other,
                risk=RiskType.medium,
                page_url=url,
                detail=f"script de terceiro > {src}",
            )
        )

    # Dado pessoal impresso na própria página (lista de clientes, depoimento com
    # CPF) é vazamento direto, não coleta — por isso risco vem do classificador.
    for classificacao in detect_in_text(soup.get_text(" ")):
        achados.append(
            RawFinding(
                finding_type=FindingType.FORM,
                category=classificacao.category,
                risk=classificacao.risk,
                page_url=url,
                detail="dado exposto no conteúdo da página",
            )
        )

    return achados


# ids de container usados por frameworks JS populares para montar a aplicação —
# um sinal forte de SPA quando esse container está vazio no HTML bruto.
SPA_ROOT_CONTAINER_IDS = ("root", "app", "__next", "__nuxt")


def _looks_like_spa_shell(html: str) -> bool:
    """Reconhece só os casos fortes, para não acionar o Playwright (lento) numa
    página comum que só tem pouco texto — como uma home simples de navegação.

    Sinal 1: <body> sem nenhum texto visível (caso degenerado, mas real).
    Sinal 2: existe um container reconhecível (#root, #app, #__next, #__nuxt) e
    ele está vazio — é exatamente a marca que create-react-app/Next/Nuxt deixam
    no HTML servido antes do JS montar a árvore.
    Qualquer página com <form> no HTML bruto nunca é tratada como casca: o
    formulário já é achado suficiente, mesmo que o resto da página seja curto.
    """
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("form") is not None:
        return False

    body = soup.find("body")
    texto_visivel = body.get_text(strip=True) if body else ""
    if not texto_visivel:
        return True

    return any(
        (root := soup.find(id=root_id)) is not None and not root.get_text(strip=True)
        for root_id in SPA_ROOT_CONTAINER_IDS
    )


def _fetch_page_with_js_fallback(url: str) -> PageResponse | None:
    """Busca a página; se parecer casca de SPA, tenta de novo com o navegador.

    Página totalmente inacessível via HTTP (timeout, DNS) não aciona o fallback:
    se o site nem responde a um GET simples, é muito improvável que um navegador
    resolva algo diferente, e a tentativa só deixaria o scan mais lento à toa.
    """
    page = fetch_page(url)
    if page is None or not _looks_like_spa_shell(page.html):
        return page

    renderizado = render_page(url)
    if renderizado is None:
        return page

    html, cookies = renderizado
    return PageResponse(html=html, cookies=cookies)


def crawl_site(base_url: str, max_pages: int = MAX_PAGES) -> CrawlResult:
    """Varre até `max_pages` páginas internas a partir de `base_url`."""
    resultado = CrawlResult()
    fila = [base_url]
    visitadas: set[str] = set()

    while fila and len(visitadas) < max_pages:
        url = fila.pop(0)
        if url in visitadas:
            continue
        visitadas.add(url)

        page = _fetch_page_with_js_fallback(url)
        if page is None:
            resultado.errors.append(f"não foi possível ler {url}")
            continue

        resultado.pages_visited.append(url)
        resultado.findings.extend(scan_page(page, url))

        soup = BeautifulSoup(page.html, "html.parser")
        for link in _extract_internal_links(soup, base_url):
            if link not in visitadas and link not in fila:
                fila.append(link)

    return _deduplicate(resultado)


def _deduplicate(resultado: CrawlResult) -> CrawlResult:
    """Um mesmo campo repetido em todas as páginas (rodapé, newsletter) é um achado só.

    A chave ignora `page_url` de propósito: sem isso, um formulário no rodapé de 20
    páginas produziria 20 linhas idênticas no relatório. Fica registrada a primeira
    página em que o achado apareceu.
    """
    vistos: set[tuple[FindingType, CategoryType, str]] = set()
    unicos: list[RawFinding] = []
    for achado in resultado.findings:
        chave = (achado.finding_type, achado.category, achado.detail)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(achado)
    resultado.findings = unicos
    return resultado
