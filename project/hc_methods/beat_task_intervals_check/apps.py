from django.apps import AppConfig

from health_check.plugins import plugin_dir


class MyAppConfig(AppConfig):
    name = "hc_methods.beat_task_intervals_check"

    def ready(self):
        from .backends import LazyBeatTasksHealthCheck, BeatTasksHealthCheck

        plugin_dir.register(LazyBeatTasksHealthCheck)
        plugin_dir.register(BeatTasksHealthCheck)
