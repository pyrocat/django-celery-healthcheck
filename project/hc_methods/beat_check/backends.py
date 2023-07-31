from django.conf import settings

from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import (
    HealthCheckException,
)

PID_FILE = settings.BASE_DIR / "healthcheck/tmp/celery_beat.pid"


class BeatCheck(BaseHealthCheckBackend):
    def check_status(self):
        if not PID_FILE.is_file():
            self.add_error(
                HealthCheckException(
                    "Celery beat has not started or --pidfile parameter is not set"
                )
            )
