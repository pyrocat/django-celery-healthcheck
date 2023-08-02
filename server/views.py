from aiohttp import web
from loguru import logger

from .healthcheck_methods.ping import CeleryPingBackend


async def healthcheck(request: web.Request) -> web.Response:
    logger.info("Healthcheck requested.")

    celery_ping = CeleryPingBackend()

    status = await celery_ping.run_check()

    if status:
        response = celery_ping.pretty_status
        data = {"Status": response}
        return web.json_response(data, status=status)

