"""Rate limiting por chave (empresa) e janela de tempo, para as rotas que
custam dinheiro ou tempo de servidor (scans e geração de documento via IA).

Redis (INCR + EXPIRE, atômico) quando REDIS_URL está configurada — funciona
corretamente com múltiplos processos/workers da API. Sem Redis, cai para um
contador em memória do próprio processo: correto para dev/CI de processo
único, mas não protege se a API rodar com múltiplos workers em produção sem
Redis configurado — por isso Redis é o caminho recomendado em produção.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, status

from app.core.config import Settings

_memory_store: dict[str, deque[float]] = defaultdict(deque)
_memory_lock = Lock()


def _limite_excedido(max_calls: int, window_seconds: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            f"Limite de {max_calls} requisições a cada {window_seconds}s "
            "excedido. Tente novamente em instantes."
        ),
    )


def _check_memory(key: str, max_calls: int, window_seconds: int) -> None:
    agora = time.monotonic()
    with _memory_lock:
        janela = _memory_store[key]
        while janela and agora - janela[0] > window_seconds:
            janela.popleft()
        if len(janela) >= max_calls:
            raise _limite_excedido(max_calls, window_seconds)
        janela.append(agora)


def _check_redis(key: str, max_calls: int, window_seconds: int) -> None:
    from app.core.queue import get_redis_connection

    conn = get_redis_connection()
    redis_key = f"ratelimit:{key}"
    contagem = conn.incr(redis_key)
    if contagem == 1:
        conn.expire(redis_key, window_seconds)
    if contagem > max_calls:
        raise _limite_excedido(max_calls, window_seconds)


def check_rate_limit(key: str, max_calls: int, window_seconds: int, settings: Settings) -> None:
    """Levanta HTTPException 429 se `key` já fez `max_calls` chamadas dentro
    dos últimos `window_seconds`. Não levanta nada quando dentro do limite."""
    if settings.redis_url:
        _check_redis(key, max_calls, window_seconds)
    else:
        _check_memory(key, max_calls, window_seconds)
