from pydantic_settings import BaseSettings


class TrandSettings(BaseSettings):
    RABBITMQ_USER: str
    RABBITMQ_PASS: str
    RABBITMQ_HOST: str
    BYBIT_RO_API_KEY: str
    BYBIT_RO_API_SECRET: str
    BYBIT_RO_IS_DEMO: bool = True

    TICKERS: list[str] = [
        "BTCUSDT",
        "ETHUSDT",
        "XRPUSDT",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
