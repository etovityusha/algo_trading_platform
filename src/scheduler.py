import logging

from faststream.rabbit import RabbitBroker
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_faststream import BrokerWrapper, StreamScheduler

logger = logging.getLogger(__name__)


class RabbitSettings(BaseModel):
    USER: str
    PASS: str
    HOST: str
    PORT: int = 5672


class SchedulerConfig(BaseSettings):
    rabbit: RabbitSettings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        env_nested_delimiter="__",
    )

    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.rabbit.USER}:{self.rabbit.PASS}@{self.rabbit.HOST}:{self.rabbit.PORT}/"


broker = RabbitBroker(url=SchedulerConfig().rabbitmq_url, logger=logger)
taskiq_broker = BrokerWrapper(broker)
taskiq_broker.task(
    queue="handle_open_positions",
    schedule=[{"cron": "* * * * *"}],
)
scheduler = StreamScheduler(
    broker=taskiq_broker,
    sources=[LabelScheduleSource(taskiq_broker)],
)
