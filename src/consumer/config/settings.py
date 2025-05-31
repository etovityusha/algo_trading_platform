from pydantic_settings import BaseSettings, SettingsConfigDict


class ConsumerSettings(BaseSettings):
    RABBITMQ_USER: str
    RABBITMQ_PASS: str
    RABBITMQ_HOST: str
    BYBIT_API_KEY: str
    BYBIT_API_SECRET: str
    BYBIT_IS_DEMO: bool = True
    SQLALCHEMY_DATABASE_URI: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )
