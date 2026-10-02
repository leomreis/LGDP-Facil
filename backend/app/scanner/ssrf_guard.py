"""Bloqueia o scanner de buscar endereços internos/privados.

O scanner recebe uma URL de qualquer usuário autenticado e a busca a partir do
servidor — sem essa checagem, é um SSRF de manual: um usuário mal-intencionado
poderia escanear `http://169.254.169.254/latest/meta-data/` (metadados de
nuvem AWS/GCP), serviços internos (`http://localhost:5432`), ou a rede privada
onde o backend roda (`http://192.168.x.x`), e ler o resultado pelo relatório.

Limitação aceita nesta v1: a validação resolve o DNS e checa o IP antes do
fetch, mas não fixa esse IP para a conexão TCP real — um ataque de DNS
rebinding (o domínio responde um IP público na checagem e um IP privado
milissegundos depois, na conexão de verdade) não é coberto. Fechar isso exige
um transport adapter customizado fixando o IP resolvido; fica registrado como
próximo passo, não como algo ignorado.
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}

# data: não faz nenhuma requisição de rede — é inerentemente seguro e usado
# nos testes do renderizador (js_renderer.py) para não depender de rede.
SAFE_SCHEMES_WITHOUT_HOST_CHECK = {"data"}


def _is_blocked_ip(ip: str) -> bool:
    endereco = ipaddress.ip_address(ip)
    return (
        endereco.is_private
        or endereco.is_loopback
        or endereco.is_link_local  # cobre 169.254.169.254 (metadados de nuvem)
        or endereco.is_multicast
        or endereco.is_reserved
        or endereco.is_unspecified
    )


def is_safe_url(url: str) -> bool:
    """True só se a URL usa http(s) e resolve exclusivamente para IPs públicos
    (ou é um esquema sem rede, como data:)."""
    partes = urlparse(url)
    if partes.scheme in SAFE_SCHEMES_WITHOUT_HOST_CHECK:
        return True
    if partes.scheme not in ALLOWED_SCHEMES or not partes.hostname:
        return False

    try:
        enderecos = socket.getaddrinfo(partes.hostname, None)
    except socket.gaierror as erro:
        logger.warning("Não foi possível resolver %s: %s", partes.hostname, erro)
        return False

    ips = {str(info[4][0]) for info in enderecos}
    if any(_is_blocked_ip(ip) for ip in ips):
        logger.warning("URL bloqueada por apontar para IP interno/privado: %s", url)
        return False

    return True
