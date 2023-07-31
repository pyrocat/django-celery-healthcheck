from celery import bootsteps
from celery.signals import worker_ready, worker_shutdown

from loguru import logger

from main.celery import app

from ..utils import HealthCheckFiles


class LivenessProbe(bootsteps.StartStopStep):
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
def worker_ready(**kwargs):
    worker = kwargs.get("sender")
    logger.info(f"Worker is ready {worker}")
    HealthCheckFiles(category=HealthCheckFiles.Category.ready).set(worker.hostname)


@worker_shutdown.connect
def worker_shutdown(**kwargs):
    logger.info(f"Worker is shutting down {kwargs}")
    worker = kwargs.get("sender")
    HealthCheckFiles(category=HealthCheckFiles.Category.ready).delete(worker.hostname)


app.steps["worker"].add(LivenessProbe)


__all__ = ["worker_ready", "worker_shutdown", "LivenessProbe"]
