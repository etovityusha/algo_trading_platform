from pydantic.main import BaseModel


class RabbitSettings(BaseModel):
    USER: str
    PASS: str
    HOST: str
    PORT: int = 5672

    @property
    def dsn(self) -> str:
        return f"amqp://{self.USER}:{self.PASS}@{self.HOST}:{self.PORT}/"


class BybitSettings(BaseModel):
    API_KEY: str
    API_SECRET: str
    IS_DEMO: bool = True


class ExchangeSettings(BaseModel):
    EXCHANGE_PROVIDER: str = "BYBIT"
    BYBIT: BybitSettings


class PostgresSettings(BaseModel):
    HOST: str
    PORT: int
    USER: str
    PASSWORD: str
    DB: str

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"

    @property
    def async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"
