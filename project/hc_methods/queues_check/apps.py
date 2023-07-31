import warnings

from celery import current_app
from django.apps import AppConfig
from django.conf import settings


from health_check.plugins import plugin_dir

from loguru import logger


class QueueHealthCheckConfig(AppConfig):
    name = "hc_methods.queues_check"

    def ready(self):
        from .backends import QueueCheck

        logger.info(f"{current_app.amqp.queues=}")
        logger.info(f"{self._registered_queues()=}")

        for queue_name in self._registered_queues():
            checker_class_name = f"QueueHealthCheck_{queue_name}"

            celery_class = type(
                checker_class_name, (QueueCheck,), {"queue": queue_name}
            )
            plugin_dir.register(celery_class)

    def _registered_queues(self) -> set[str]:
        routes = settings.CELERY_TASK_ROUTES
        if not routes:
            return set()
        return set([q for q in routes.values()])
