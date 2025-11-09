from environs import Env

from configs import PostgresSettings, RabbitSettings


class BacktesterSettings:
    def __init__(self) -> None:
        env = Env()
        env.read_env()

        self.rabbit = RabbitSettings(
            USER=env.str("RABBIT__USER"),
            PASS=env.str("RABBIT__PASS"),
            HOST=env.str("RABBIT__HOST"),
            PORT=env.int("RABBIT__PORT", 5672),
        )

        self.postgres = PostgresSettings(
            HOST=env.str("POSTGRES__HOST"),
            PORT=env.int("POSTGRES__PORT"),
            USER=env.str("POSTGRES__USER"),
            PASSWORD=env.str("POSTGRES__PASSWORD"),
            DB=env.str("POSTGRES__DB"),
        )

        self.bybit_api_key = env.str("BYBIT_RO__API_KEY")
        self.bybit_api_secret = env.str("BYBIT_RO__API_SECRET")
        self.bybit_is_demo = env.bool("BYBIT__IS_DEMO", False)
