from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def _migrate(conn):
    """Lightweight migrations: add columns that may be missing on older DBs."""
    from sqlalchemy import text
    result = await conn.execute(text("PRAGMA table_info(photos)"))
    columns = {row[1] for row in result.fetchall()}
    if "country_code" not in columns:
        await conn.execute(text("ALTER TABLE photos ADD COLUMN country_code VARCHAR"))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate(conn)
