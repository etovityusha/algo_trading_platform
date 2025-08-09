from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitSettings(BaseModel):
    USER: str
    PASS: str
    HOST: str
    PORT: int = 5672


class BybitReadOnlySettings(BaseModel):
    API_KEY: str
    API_SECRET: str
    IS_DEMO: bool = True


class TrandSettings(BaseSettings):
    rabbit: RabbitSettings
    bybit_ro: BybitReadOnlySettings

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
