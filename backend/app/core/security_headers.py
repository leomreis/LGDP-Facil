"""Cabeçalhos de segurança aplicados a toda resposta da API.

Defesa em profundidade: a API só serve JSON (exceto /docs e /redoc, a
documentação interativa do FastAPI), então o risco que esses cabeçalhos
mitigam — a resposta sendo interpretada como HTML/script pelo navegador — já é
baixo. Ainda assim, custam nada e cobrem qualquer rota futura que sirva HTML
por engano.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# /docs e /redoc carregam JS/CSS de CDN (cdn.jsdelivr.net) para renderizar a
# UI do Swagger/ReDoc — um CSP restrito quebraria a página. É documentação
# interativa de desenvolvimento, não uma rota de dado do usuário.
_PATHS_SEM_CSP = ("/docs", "/redoc")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # HSTS não tem efeito sobre HTTP puro (dev) — o navegador só honra o
        # cabeçalho em respostas já servidas via HTTPS, então é seguro sempre enviar.
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        if not request.url.path.startswith(_PATHS_SEM_CSP):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )

        return response
