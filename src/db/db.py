from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from core.settings import settings

engine = create_async_engine(
    url=settings.DATABASE_DSN,
    echo=settings.DEBUG,
)

async_session = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession,
)


async def get_db_session() -> AsyncSession:
    async with async_session() as session_:
        yield session_
