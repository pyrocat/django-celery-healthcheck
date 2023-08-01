import asyncio
from pathlib import Path
from aiohttp import web

from .routes import setup_routes
from .utils import  Config

#
#
# async def setup_redis(app, conf):
#     redis = await init_redis(conf.redis)
#     app["redis"] = redis
#     return redis


async def init():
    config = Config().load()
    app = web.Application()
    setup_routes(app)
    port = config.port
    return app, port


def main():
    loop = asyncio.get_event_loop()
    app, port = loop.run_until_complete(init())
    web.run_app(app, port=port)


__all__ = ["main"]

if __name__ == "__main__":
    main()