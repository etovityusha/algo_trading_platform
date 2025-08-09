from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitSettings(BaseModel):
    USER: str
    PASS: str
    HOST: str
    PORT: int = 5672


class BybitSettings(BaseModel):
    API_KEY: str
    API_SECRET: str
    IS_DEMO: bool = True


class ConsumerSettings(BaseSettings):
    rabbit: RabbitSettings
    bybit: BybitSettings
    SQLALCHEMY_DATABASE_URI: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        env_nested_delimiter="__",
    )
