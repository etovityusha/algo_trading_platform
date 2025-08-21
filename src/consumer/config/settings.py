from pydantic_settings import BaseSettings, SettingsConfigDict

from configs import BybitSettings, PostgresSettings, RabbitSettings


class ConsumerSettings(BaseSettings):
    rabbit: RabbitSettings
    bybit: BybitSettings
    postgres: PostgresSettings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        env_nested_delimiter="__",
    )
