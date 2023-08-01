import os
from celery import Celery
from .monitors import EventsCamera


def main(app, freq=1.0):
    state = app.events.State()

    with app.connection() as connection:
        recv = app.events.Receiver(connection, handlers={"*": state.event})
        with EventsCamera(state, freq=freq):
            recv.capture(limit=None, timeout=None)


if __name__ == "__main__":
    app = Celery(
        "main", broker=os.getenv("CELERY_BROKER"), backend=os.getenv("CELERY_BACKEND")
    )
    main(app)
