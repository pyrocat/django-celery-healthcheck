import asyncio
from enum import IntEnum
from loguru import logger


class HTTPStatus(IntEnum):
    HTTP_200_OK = 200
    HTTP_500_INTERNAL_SERVER_ERROR = 500


class HealthCheckException(Exception):
    ...


class AsyncBaseHealthCheckBackend:
    critical_service = True

    def __init__(self):
        self.errors = []

    async def check_status(self):
        raise NotImplementedError

    async def run_check(self) -> HTTPStatus:
        self.errors = []
        status = HTTPStatus.HTTP_200_OK
        try:
            await self.check_status()
        except HealthCheckException as e:
            if self.critical_service:
                status = HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
            self.add_error(e, e)
        except BaseException:
            logger.exception("Unexpected Error!")
            raise
        return status

    def add_error(self, error, cause=None):
        if isinstance(error, HealthCheckException):
            pass
        elif isinstance(error, str):
            msg = error
            error = HealthCheckException(msg)
        else:
            msg = "unknown error"
            error = HealthCheckException(msg)
        if isinstance(cause, BaseException):
            logger.exception(str(error))
        else:
            logger.error(str(error))
        self.errors.append(error)

    @property
    def pretty_status(self):
        if self.errors:
            return "\n".join(str(e) for e in self.errors)
        return "OK"

    @property
    def status(self):
        return int(not self.errors)

    def identifier(self):
        return self.__class__.__name__
