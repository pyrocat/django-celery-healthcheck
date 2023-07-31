from django.apps import AppConfig

from health_check.plugins import plugin_dir


class MyAppConfig(AppConfig):
    name = "hc_methods.workers_check"

    def ready(self):
        from .backends import WorkersHealthCheck

        plugin_dir.register(WorkersHealthCheck)
