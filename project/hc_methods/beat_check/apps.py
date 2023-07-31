from django.apps import AppConfig
from django.conf import settings

from health_check.plugins import plugin_dir


class QueueHealthCheckConfig(AppConfig):
    name = "hc_methods.beat_check"

    def ready(self):
        from .backends import BeatCheck
        plugin_dir.register(BeatCheck)

