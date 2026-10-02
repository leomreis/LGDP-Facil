"""Fila de scans via RQ/Redis.

`get_queue()` é o único ponto que a API e o worker compartilham: a API enfileira
aqui, o worker (app/worker.py) consome daqui. Trocar de fila (ex.: outro broker)
significa mexer só neste arquivo.
"""

from functools import lru_cache

import redis
from rq import Queue

from app.core.config import get_settings

SCAN_QUEUE_NAME = "scans"


@lru_cache
def get_redis_connection() -> redis.Redis:
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL não configurada")
    return redis.from_url(settings.redis_url)


def get_queue() -> Queue:
    return Queue(SCAN_QUEUE_NAME, connection=get_redis_connection())
