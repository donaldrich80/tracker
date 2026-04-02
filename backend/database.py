from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import os

DB_PATH = os.getenv("DB_PATH", "./data/tracker.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_fts_table():
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts "
            "USING fts5(id UNINDEXED, title, description, acceptance)"
        ))


async def create_tables():
    async with engine.begin() as conn:
        from backend import models  # noqa: F401 — registers models
        await conn.run_sync(Base.metadata.create_all)
    await create_fts_table()
