import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def build_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    user = os.getenv("POSTGRES_USER", "postgres")
    pwd = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "postgres")
    return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"


DATABASE_URL = build_database_url()


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
