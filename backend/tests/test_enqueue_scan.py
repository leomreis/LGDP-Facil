import uuid

import pytest
from fastapi import BackgroundTasks

from app.core.config import Settings, get_settings
from app.services.scan_service import enqueue_scan


class TestEnqueueScanSemRedis:
    def test_usa_background_tasks_quando_redis_url_vazia(self):
        settings = Settings()
        settings.redis_url = ""
        background_tasks = BackgroundTasks()
        scan_id = uuid.uuid4()

        enqueue_scan(scan_id, background_tasks, settings)

        assert len(background_tasks.tasks) == 1


class TestEnqueueScanComRedis:
    @pytest.fixture(autouse=True)
    def redis_disponivel(self):
        if not get_settings().redis_url:
            pytest.skip("REDIS_URL não configurada — teste pulado")

    def test_usa_rq_quando_redis_url_configurada(self):
        from app.core.queue import get_queue

        settings = get_settings()
        background_tasks = BackgroundTasks()
        scan_id = uuid.uuid4()

        enqueue_scan(scan_id, background_tasks, settings)

        assert len(background_tasks.tasks) == 0  # não usou o fallback

        fila = get_queue()
        jobs = fila.jobs
        assert any(str(scan_id) in str(job.args) for job in jobs)
        fila.connection.flushdb()
