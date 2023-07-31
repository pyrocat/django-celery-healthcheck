from django.conf import settings
from django.utils import timezone

from celery.events.snapshot import Polaroid

from hc_methods.utils import HealthcheckStorage


from loguru import logger


class TasksCamera(Polaroid):
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


def tasks_listener(app, freq=settings.HEALTHCHECK_PROBE_INTERVAL):
    state = app.events.State()
    with app.connection() as connection:
        recv = app.events.Receiver(connection, handlers={"task-started": state.event})
        with TasksCamera(state, freq=freq):
            recv.capture(limit=None, timeout=None)


__all__ = ["TasksCamera"]
