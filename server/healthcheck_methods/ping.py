import asyncio
from celery import Celery
from ..utils import Config

from loguru import logger

from .base import AsyncBaseHealthCheckBackend


class CeleryPingBackend(AsyncBaseHealthCheckBackend):
    CORRECT_PING_RESPONSE = {"ok": "pong"}

    async def ping_celery(self):
        config = Config().load()
        celery_app = Celery(
            "main", broker=config.celery.broker, backend=config.celery.backend
        )
        res = await asyncio.to_thread(celery_app.control.ping)

        return res

    async def _check_ping_result(self, ping_result):
        for result in ping_result:
            worker, response = list(result.items())[0]
            if response != self.CORRECT_PING_RESPONSE:
                self.add_error(f"Celery worker {worker} response was incorrect")
                continue

    async def check_status(self):
        ping_data: list[dict] = await self.ping_celery()
        logger.info(ping_data)

        return await self._check_ping_result(ping_data)


__all__ = ["CeleryPingBackend"]
