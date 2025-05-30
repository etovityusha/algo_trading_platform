from pydantic_settings import BaseSettings


class ConsumerSettings(BaseSettings):
    RABBITMQ_USER: str
    RABBITMQ_PASS: str
    RABBITMQ_HOST: str
    BYBIT_API_KEY: str
    BYBIT_API_SECRET: str
    BYBIT_IS_DEMO: bool = True
    SQLALCHEMY_DATABASE_URI: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
