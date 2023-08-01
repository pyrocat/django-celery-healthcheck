from health_check.backends import BaseHealthCheckBackend
from datetime import datetime, timedelta
from django.utils import timezone

import celery
from celery.beat import Service
from health_check.exceptions import (
    HealthCheckException,
)
from django.conf import settings
from django_celery_beat.models import PeriodicTask

from ..storages import HealthcheckStorage

from loguru import logger

TTL = timedelta(seconds=settings.HEALTHCHECK_STORAGE_TTL)
INTERVAL = timedelta(seconds=settings.HEALTHCHECK_PROBE_INTERVAL)


class BeatHealthCheckBase(BaseHealthCheckBackend):
    @property
    def active_tasks(self):
        return PeriodicTask.objects.filter(enabled=True).exclude(last_run_at=None)

    @property
    def sync_interval(self) -> timedelta:
        # 0 means sync is performed with intervals of N seconds
        # (180 by default)
        beat_sync_every = getattr(settings, "CELERYBEAT_SYNC_EVERY", 0)

        if not beat_sync_every:
            return timedelta(
                seconds=Service(celery.current_app).get_scheduler().sync_every
            )
        else:
            return timedelta()

    def _get_last_run_realtime(self, task_name: str) -> datetime:
        storage = HealthcheckStorage()
        logger.info(f"Getting timestamp for task {task_name}: {storage.get(task_name)}")
        return storage.get(task_name)

    def check_interval_lazy(self, periodic_task: PeriodicTask) -> bool:
        return periodic_task.schedule.now() < (
            periodic_task.last_run_at
            + periodic_task.schedule.run_every
            + self.sync_interval
        )

    def check_interval_realtime(self, periodic_task: PeriodicTask) -> bool:
        last_run_at = self._get_last_run_realtime(periodic_task.task)

        # Record removed from redis, but interval is less than ttl
        if not last_run_at and periodic_task.schedule.run_every < TTL:
            return False

        # Fallback in case last record might be missing because of short TTL
        if not last_run_at and periodic_task.schedule.run_every > TTL:
            return self.check_interval_lazy(periodic_task)

        return timezone.now() < (
            last_run_at + periodic_task.schedule.run_every + INTERVAL
        )

    def check_remaining_estimate(self, periodic_task: PeriodicTask) -> bool:
        last_run_at = (
            self._get_last_run_realtime(periodic_task.task) or periodic_task.last_run_at
        )

        return (
            timedelta()
            < periodic_task.schedule.remaining_estimate(last_run_at) + INTERVAL
        )


class LazyBeatTasksHealthCheck(BeatHealthCheckBase):
    #: The status endpoints will respond with a 200 status code
    #: even if the check errors.
    critical_service = False

    def check_status(self):
        for periodic_task in self.active_tasks:
            try:
                periodic_task.schedule.run_every
            except AttributeError:
                check = self.check_remaining_estimate(periodic_task)
            else:
                check = self.check_interval_lazy(periodic_task)

            if not check:
                self.add_error(
                    HealthCheckException(
                        f"Sheduled task {periodic_task.task} has not run "
                        f"for too long"
                    )
                )


class BeatTasksHealthCheck(BeatHealthCheckBase):
    #: The status endpoints will respond with a 200 status code
    #: even if the check errors.
    critical_service = False

    def check_status(self):
        for periodic_task in self.active_tasks:
            try:
                periodic_task.schedule.run_every
            except AttributeError:
                check = self.check_remaining_estimate(periodic_task)
            else:
                check = self.check_interval_realtime(periodic_task)

            if not check:
                self.add_error(
                    HealthCheckException(
                        f"Sheduled task {periodic_task.task} has not run "
                        f"for too long"
                    )
                )
