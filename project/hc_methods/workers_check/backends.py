from health_check.backends import BaseHealthCheckBackend
from datetime import datetime, timedelta
from django.utils import timezone

from health_check.exceptions import HealthCheckException

from django.conf import settings

from ..storages import HealthCheckFiles, HealthRecordNotFound
from loguru import logger


_timeout = timedelta(seconds=settings.HEALTHCHECK_WORKER_TIMEOUT)


class WorkersHealthCheck(BaseHealthCheckBackend):
    #: The status endpoints will respond with a 200 status code
    #: even if the check errors.
    critical_service = False

    def check_status(self):
        self._check_active()

    def _check_active(self):
        now = timezone.now()

        active_workers = HealthCheckFiles(category=HealthCheckFiles.Category.alive)
        ready_workers = HealthCheckFiles(category=HealthCheckFiles.Category.ready)

        logger.debug(f"{active_workers.get_keys()=}  {ready_workers.get_keys()=}")

        for hostname in ready_workers.get_keys():
            try:
                if now - active_workers.get(hostname) > _timeout:
                    self.add_error(
                        HealthCheckException(
                            f"Worker {hostname} has been inactive more than "
                            f"{settings.HEALTHCHECK_WORKER_TIMEOUT} seconds"
                        )
                    )
            except HealthRecordNotFound:
                self.add_error(
                    HealthCheckException(
                        f"Worker {hostname} once started,  " f"is no longer active"
                    )
                )
