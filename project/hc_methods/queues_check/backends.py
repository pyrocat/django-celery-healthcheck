from celery.exceptions import TaskRevokedError, TimeoutError
from celery import current_app as app
from django.conf import settings

from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import (
    ServiceReturnedUnexpectedResult,
    ServiceUnavailable,
    HealthCheckException,
)

from .tasks import add


class QueueCheck(BaseHealthCheckBackend):
    timeout = getattr(settings, "HEALTHCHECK_CELERY_TIMEOUT", 3)
    result_timeout = getattr(settings, "HEALTHCHECK_CELERY_RESULT_TIMEOUT", timeout)
    queue_timeout = getattr(settings, "HEALTHCHECK_CELERY_QUEUE_TIMEOUT", timeout)

    def check_status(self):
        self._check_active()
        self._check_goes_through()

    def _check_active(self):
        active_queues = [
            queue["name"]
            for values in app.control.inspect().active_queues().values()
            for queue in values
        ]
        if self.queue not in active_queues:
            self.add_error(
                HealthCheckException(
                    f"The queue is not among the active queues:{active_queues}"
                )
            )

    def _check_goes_through(self):
        try:
            result = add.apply_async(
                args=[4, 4], expires=self.queue_timeout, queue=self.queue
            )
            result.get(timeout=self.result_timeout)
            if result.result != 8:
                self.add_error(
                    ServiceReturnedUnexpectedResult("Celery returned wrong result")
                )
        except IOError as e:
            self.add_error(ServiceUnavailable("IOError"), e)
        except NotImplementedError as e:
            self.add_error(
                ServiceUnavailable(
                    "NotImplementedError: Make sure CELERY_RESULT_BACKEND is set"
                ),
                e,
            )
        except TaskRevokedError as e:
            self.add_error(
                ServiceUnavailable(
                    "TaskRevokedError: The task was revoked, likely because it spent "
                    "too long in the queue"
                ),
                e,
            )
        except TimeoutError as e:
            self.add_error(
                ServiceUnavailable(
                    "TimeoutError: The task took too long to return a result"
                ),
                e,
            )
        except BaseException as e:
            self.add_error(ServiceUnavailable("Unknown error"), e)
