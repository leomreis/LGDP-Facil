"""Processo worker: consome a fila `scans` e executa `run_scan`.

Roda separado da API (`uvicorn app.main:app`). Em dev, um terminal para cada:

    uvicorn app.main:app --reload
    python -m app.worker

Sem REDIS_URL configurada, a API cai para BackgroundTasks e este worker não é
necessário — ver app/core/config.py e app/api/scans.py.
"""

import logging
import sys

from rq import SimpleWorker, Worker

from app.core.config import get_settings
from app.core.observability import init_sentry
from app.core.queue import SCAN_QUEUE_NAME, get_redis_connection

logging.basicConfig(level=logging.INFO)

# O Worker padrão do RQ isola cada job num processo filho via os.fork(), que não
# existe no Windows (AttributeError: module 'os' has no attribute 'fork').
# SimpleWorker roda o job no mesmo processo — sem essa isolação, mas funciona em
# qualquer SO. Em produção (Linux), o Worker padrão é preferível.
WorkerClass = SimpleWorker if sys.platform == "win32" else Worker


def main() -> None:
    init_sentry(get_settings())
    worker = WorkerClass([SCAN_QUEUE_NAME], connection=get_redis_connection())
    worker.work()


if __name__ == "__main__":
    main()
