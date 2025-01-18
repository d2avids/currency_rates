import decimal
import os
from typing import Annotated

from dotenv import find_dotenv, load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode

load_dotenv(find_dotenv())

RUN_TYPE = os.getenv('RUN_TYPE', 'DOCKER')


class CurrencyParseSettings(BaseSettings):
    CURRENCIES_URL: str
    CURRENCY_RATE_START_PATTERN: str
    CURRENCY_RATE_END_PATTERN: str
    RATE_KEY: str

    DECIMAL_PLACES: decimal.Decimal = decimal.Decimal(os.getenv('DECIMAL_PLACES', '0.00000001'))
    MAX_RATES_PER_REQUEST: int = 100
    SESSION_TIMEOUT: int = 5


class Security(BaseSettings):
    ALLOWED_HOSTS: Annotated[list[str], NoDecode]
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode]
    RATE_LIMIT: int = 10
    RATE_LIMIT_INTERVAL_MINUTES: int = 10

    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def decode_allowed_origins(cls, v: str) -> list[str]:
        return [origin for origin in v.split(',')]

    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def decode_allowed_hosts(cls, v: str) -> list[str]:
        return [host for host in v.split(',')]


class Settings(BaseSettings):
    API_KEY_NAME: str
    API_KEYS: Annotated[list[str], NoDecode]
    UNLIMITED_API_KEYS: Annotated[list[str], NoDecode]
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    PROJECT_NAME: str

    HOST: str = '0.0.0.0'
    PORT: int = 8080
    DOCS_URL: str = '/docs'
    OPENAPI_URL: str = '/docs/openapi.json'

    POSTGRES_VERSION: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    REDIS_HOST: str = 'redis'
    REDIS_PORT: int = 6379

    currency_parsing_settings: CurrencyParseSettings = CurrencyParseSettings()
    security: Security = Security()

    @property
    def DATABASE_DSN(self) -> str:
        hostname = 'postgres' if RUN_TYPE == 'DOCKER' else 'localhost'
        return (
            f'postgresql+asyncpg://'
            f'{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}'
            f'@{hostname}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}'
        )

    @field_validator('API_KEYS', mode='before')
    @classmethod
    def decode_api_keys(cls, v: str) -> list[str]:
        return [api_key for api_key in v.split(',')]

    @field_validator('UNLIMITED_API_KEYS', mode='before')
    @classmethod
    def decode_unlimited_api_keys(cls, v: str) -> list[str]:
        return [api_key for api_key in v.split(',')]


settings = Settings()
