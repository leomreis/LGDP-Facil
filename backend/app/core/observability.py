"""Inicialização opcional de observabilidade (Sentry).

`init_sentry()` é chamado uma vez, na subida da API e do worker. Sem
SENTRY_DSN configurada, é um no-op — o projeto roda normalmente sem conta
nenhuma no Sentry, como hoje.
"""

import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        # Volume baixo esperado (poucas PMEs em validação) — captura tudo por
        # enquanto. Reduzir se o volume de requisições crescer.
        traces_sample_rate=1.0,
    )
    logger.info("Sentry inicializado (environment=%s)", settings.environment)
