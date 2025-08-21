from pydantic_settings import BaseSettings, SettingsConfigDict

from configs import BybitSettings, RabbitSettings


class TrandSettings(BaseSettings):
    rabbit: RabbitSettings
    bybit_ro: BybitSettings

    TICKERS: list[str] = [
        "BTCUSDT",
        "ETHUSDT",
        "XRPUSDT",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )
