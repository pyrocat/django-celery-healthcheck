from aiohttp import web
import asyncio
from loguru import logger
from server.utils import Config
import celery


class ServiceUnavailable(Exception):
    ...


async def ping_celery():
    config = Config().load()
    celery_app = celery.Celery(
        "main", broker=config.celery.broker, backend=config.celery.backend
    )
    res = await asyncio.to_thread(celery_app.control.ping)

    return res


async def verify_status():
    ping_data: list[dict] = await ping_celery()
    logger.info(ping_data)

    return await _check_ping_result(ping_data)


async def _check_ping_result(ping_result):
    CORRECT_PING_RESPONSE = {"ok": "pong"}

    active_workers = []
    errors = []

    for result in ping_result:
        worker, response = list(result.items())[0]
        if response != CORRECT_PING_RESPONSE:
            errors.append(f"Celery worker {worker} response was incorrect")
            continue
    if not errors:
        return "Ok", 200
    return errors, 500


async def healthcheck(request: web.Request) -> web.Response:
    logger.info("Healthcheck requested.")

    response, status = await verify_status()

    data = {"Status": response}
    return web.json_response(data, status=status)
