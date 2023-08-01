import yaml
from typing import Optional

from pathlib import Path
from pydantic import BaseModel

from loguru import logger


BASE_DIR = Path(__file__).parent


CONFIG_PATH = BASE_DIR / "config" / "config.yaml"

logger.debug(f"{BASE_DIR=}  {CONFIG_PATH=}")


class RedisConfig(BaseModel):
    host: str
    port: str
    db: int
    minsize: int
    maxsize: int


class CeleryConfig(BaseModel):
    broker: str
    backend: str


class Config(BaseModel):
    redis: Optional[RedisConfig]
    celery: Optional[CeleryConfig]
    host: Optional[str]
    port: Optional[int]

    @classmethod
    def load(cls, filepath: Path = CONFIG_PATH):
        with open(filepath, "rt") as f:
            data = yaml.safe_load(f)
        return cls.parse_obj(data)
