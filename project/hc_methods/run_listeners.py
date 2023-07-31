from django.conf import settings


def tasks_listener(app, freq=settings.HEALTHCHECK_PROBE_INTERVAL):
    state = app.events.State()
    with app.connection() as connection:
        recv = app.events.Receiver(connection, handlers={"task-started": state.event})
        with TasksCamera(state, freq=freq):
            recv.capture(limit=None, timeout=None)


if __name__ == "__main__":
    ...