from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]
    admin: int


@dataclass
class Postgres:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class Redis:
    host: str
    port: int
    password: str


@dataclass
class ConfigEnv:
    tg_bot: TgBot
    postgres: Postgres
    redis: Redis


# Создаем функцию, которая будет читать файл .env и возвращать
# экземпляр класса Config с заполненными полями token и admin_ids
def load_config(path: str | None = None) -> ConfigEnv:
    env = Env()
    env.read_env(path)
    return ConfigEnv(
        tg_bot=TgBot(
            token=env('BOT_TOKEN'),
            admin_ids=list(map(int, env.list('ADMIN_IDS'))),
            admin=env('ADMIN')
        ),
        postgres=Postgres(
            host=env('POSTGRES_HOST'),
            port=env('POSTGRES_PORT'),
            user=env('POSTGRES_USER'),
            password=env('POSTGRES_PASSWORD'),
            database=env('POSTGRES_DB'),
        ),
        redis=Redis(
            host=env('REDIS_HOST'),
            port=env('REDIS_PORT'),
            password=env('REDIS_PASSWORD'),
        ),
    )


config: ConfigEnv = load_config()


def DATABASE_URL_asyncpg():
    # DNS
    # postgresql+asyncpg://postgres:postgres@localhost:5432/sa
    return f'postgresql+asyncpg://{config.postgres.user}:{config.postgres.password}@{config.postgres.host}:{config.postgres.port}/{config.postgres.database}'


def DATABASE_URL_psycorg():
    # DNS
    # postgresql+psycopg://postgres:postgres@localhost:5432/sa
    return f'postgresql+psycopg://{config.postgres.user}:{config.postgres.password}@{config.postgres.host}:{config.postgres.port}/{config.postgres.database}'
