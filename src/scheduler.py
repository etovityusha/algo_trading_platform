import logging

from faststream.rabbit import RabbitBroker
from pydantic_settings import BaseSettings, SettingsConfigDict
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_faststream import BrokerWrapper, StreamScheduler

from configs import RabbitSettings

logger = logging.getLogger(__name__)


class SchedulerConfig(BaseSettings):
    rabbit: RabbitSettings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        env_nested_delimiter="__",
    )


broker = RabbitBroker(url=SchedulerConfig().rabbit.dsn, logger=logger)
taskiq_broker = BrokerWrapper(broker)
taskiq_broker.task(
    queue="handle_open_positions",
    schedule=[{"cron": "* * * * *"}],
)
scheduler = StreamScheduler(
    broker=taskiq_broker,
    sources=[LabelScheduleSource(taskiq_broker)],
)
