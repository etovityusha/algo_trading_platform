from pydantic_settings import BaseSettings


class MigratorConfig(BaseSettings):
    SQLALCHEMY_DATABASE_URI: str

    class Config:
        env_file = ".env"
        extra = "ignore"
