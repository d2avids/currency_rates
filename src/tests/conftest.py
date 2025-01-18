from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

project_root = Path(__file__).resolve().parents[2]

env_file = project_root / '.env'
env_example_file = project_root / '.env_example'

if env_file.exists():
    load_dotenv(dotenv_path=env_file)
elif env_example_file.exists():
    load_dotenv(dotenv_path=env_example_file)
else:
    raise FileNotFoundError('Neither .env nor .env_example was found in the project root.')


from domain.base import Base
from core.settings import settings
from main import app

POSTGRES_IMAGE = f'postgres:{settings.POSTGRES_VERSION}'


@pytest.fixture(scope='function')
def test_client():
    return TestClient(app=app)


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    """Spin up Postgres in Docker once for the entire test session (sync)."""
    container = PostgresContainer(POSTGRES_IMAGE)
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def db_url(postgres_container) -> str:
    """
    1) Build a sync URL from the container.
    2) Create a sync engine.
    3) Create all tables via Base.metadata.create_all(sync_engine).
    4) Return an *async* url string for the tests.
    """
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return async_url


@pytest_asyncio.fixture
async def db_session(db_url):
    """
    Return a fresh AsyncSession for each test,
    using the already-prepared async DB url.
    """
    async_engine = create_async_engine(db_url, echo=False, future=True)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session

    await async_engine.dispose()


@pytest.fixture
def currency_rate_repo(db_session):
    from repositories.currency_rates import CurrencyRateRepo
    return CurrencyRateRepo(db_session)
