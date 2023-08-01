from main import celery_app
from celery import bootsteps
from celery.signals import worker_ready, worker_shutdown
from django.conf import settings
from django.utils import timezone

from celery.events.snapshot import Polaroid

from hc_methods.storages import HealthcheckStorage, HealthCheckFiles

from loguru import logger


class EventsCamera(Polaroid):
    clear_after = True  # clear after flush (incl, state.event_count).

    def on_shutter(self, state):
        if not state.event_count:
            # No new events since last snapshot.
            return

        redis = HealthcheckStorage(ttl=settings.HEALTHCHECK_STORAGE_TTL)

        logger.debug(f"{state.tasks=}")
        logger.debug(f"{state.workers=}")

        for worker in state.workers.values():
            logger.info(f"{worker.hostname} is alive")
            redis.set(worker.hostname)

        for task in state.tasks.values():
            logger.info(f"{task.name}")
            redis.set(task.name)


class LivenessProbe(bootsteps.StartStopStep):
    """
    A hook for workers. Periodically Updates the timestamp of a temp file
    as long as the worker is alive.
    """

    requires = {"celery.worker.components:Timer"}

    def __init__(self, worker, **kwargs):
        self.requests = []
        self.tref = None
        self.heartbeat_storage = HealthCheckFiles(
            category=HealthCheckFiles.Category.alive
        )

    def start(self, worker):
        self.tref = worker.timer.call_repeatedly(
            1.0,
            self.update_heartbeat_file,
            (worker,),
            priority=10,
        )

    def stop(self, worker):
        self.heartbeat_storage.delete(worker.hostname)

    def update_heartbeat_file(self, worker):
        self.heartbeat_storage.set(worker.hostname)


@worker_ready.connect
def worker_ready_callback(**kwargs):
    worker = kwargs.get("sender")
    logger.info(f"Worker is ready {worker}")
    HealthCheckFiles(category=HealthCheckFiles.Category.ready).set(worker.hostname)


@worker_shutdown.connect
def worker_shutdown_callback(**kwargs):
    logger.info(f"Worker is shutting down {kwargs}")
    worker = kwargs.get("sender")
    HealthCheckFiles(category=HealthCheckFiles.Category.ready).delete(worker.hostname)


celery_app.steps["worker"].add(LivenessProbe)


__all__ = [
    "EventsCamera",
    "LivenessProbe",
    "worker_ready_callback",
    "worker_shutdown_callback",
]
