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
    if "media_type" not in columns:
        await conn.execute(text(
            "ALTER TABLE photos ADD COLUMN media_type VARCHAR DEFAULT 'photo'"
        ))
        await conn.execute(text("""
            UPDATE photos SET media_type = 'video'
            WHERE lower(filename) LIKE '%.mp4'
               OR lower(filename) LIKE '%.mov'
               OR lower(filename) LIKE '%.avi'
               OR lower(filename) LIKE '%.mkv'
               OR lower(filename) LIKE '%.m4v'
               OR lower(filename) LIKE '%.3gp'
        """))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate(conn)
