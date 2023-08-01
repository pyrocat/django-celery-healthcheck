import threading
import time
from pprint import pformat
from main import celery_app
from celery import bootsteps, Celery
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


celery_app.steps["worker"].add(LivenessProbe)


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


class LoggerCam(Polaroid):
    clear_after = True  # clear after flush (incl, state.event_count).

    def on_shutter(self, state):
        if not state.event_count:
            # No new events since last snapshot.
            return
        logger.info("Workers: {0}".format(pformat(state.workers, indent=4)))
        logger.info("Tasks: {0}".format(pformat(state.tasks, indent=4)))
        logger.info("Total: {0.event_count} events, {0.task_count} tasks".format(state))


class RealtimeMonitor(threading.Thread):
    def __init__(self, app: Celery, freq: int):
        threading.Thread.__init__(self)
        self.app = app
        self.try_interval = freq
        self.state = app.events.State()
        logger.info(f"Initialized {self}")

    def _on_task_start(self, event):
        task = self.state.tasks.get(event["uuid"])
        logger.debug(f"Task {task.name} has launched")

    def _on_worker_online(self, event):
        worker = self.state.workers.get(event["uuid"])
        logger.debug(f"Task {worker.hostname} has launched")

    def _on_worker_heartbeat(self, event):
        worker = self.state.workers.get(event["uuid"])
        logger.debug(f"Worker {worker.hostname} has sent heartbeat")

    def _on_worker_offline(self, event):
        worker = self.state.workers.get(event["uuid"])
        logger.debug(f"Worker {worker.hostname} has gone offline")

    def run(self):
        logger.info(f"{self.__class__.__name__} has run")
        while True:
            try:
                with self.app.connection() as conn:
                    recv = self.app.events.Receiver(
                        conn,
                        handlers={
                            "task-started": self._on_task_start,
                            "worker-online": self._on_worker_online,
                            "worker-heartbeat": self._on_worker_heartbeat,
                            "worker-offline": self._on_worker_offline,
                            "*": self.state.event,
                        },
                        # При масштабировании пользоваться одной очередью
                        node_id="app_event_receiver",
                    )
                    recv.capture(limit=None, timeout=None, wakeup=True)
            except (SystemExit, KeyboardInterrupt):
                self.join()
            except Exception as e:
                logger.error(f"No events, trying again in {self.try_interval} seconds")
                time.sleep(self.try_interval)


__all__ = [
    "EventsCamera",
    "LivenessProbe",
    "worker_ready_callback",
    "worker_shutdown_callback",
    "RealtimeMonitor",
]
