import time

from celery import shared_task


@shared_task(queue="first_queue")
def just_sleep():
    time.sleep(10)
    return True


@shared_task(queue="second_queue")
def sleep_tenfold(times):
    time.sleep(int(times) * 10)
    return True


__all__ = ["just_sleep", "sleep_tenfold"]