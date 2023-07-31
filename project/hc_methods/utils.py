from enum import StrEnum

from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

from django.utils import timezone
from django.conf import settings
from loguru import logger
from redis import Redis


class RedisClient:
    def __init__(self, db=0):
        self.client = Redis.from_url(f"{settings.REDIS_URL}/{db}")

    def __enter__(self):
        if not self.client.ping():
            raise ConnectionError("Can not ping Redis.")
        return self.client

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        self.client.close()
        return False  # Do not suppress exceptions

    def __del__(self) -> None:
        self.client.close()


class HealthcheckStorage:
    client: Redis

    def __init__(self, ttl: int = None, db: int = 5):
        self.ttl = ttl
        self.db = db

    def set(self, key: str):
        timestamp = timezone.now().isoformat()
        with RedisClient(self.db) as self.client:
            self.client.set(key, timestamp, ex=self.ttl)

    def get(self, key) -> datetime:
        with RedisClient(self.db) as self.client:
            value = self.client.get(key)
            if value:
                return datetime.fromisoformat(value.decode())


class HealthRecordNotFound(Exception):
    ...


class HealthCheckFiles:
    TEMPDIR = settings.BASE_DIR / "tmp"

    class Category(StrEnum):
        alive = "alive"
        ready = "ready"

    def __init__(self, category: Category | None):
        self.folder = self.TEMPDIR / category if category else self.TEMPDIR
        self.folder.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> datetime:
        file = self.folder / key

        if not file.exists():
            raise HealthRecordNotFound(key)

        # file timestamp is naive
        return datetime.fromtimestamp(
            file.stat().st_mtime, tz=timezone.get_current_timezone()
        )

    def set(self, key: str):
        file = self.folder / key
        file.touch()

    def delete(self, key: str):
        file = self.folder / key
        file.unlink(missing_ok=True)

    def get_keys(self) -> list[str]:
        return [item.stem for item in self.folder.glob("*")]
