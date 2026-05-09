import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from pypersim_demo.config import Settings
from pypersim_demo.db.engine import create_engine, init_db, session_factory


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path)


def test_create_engine_returns_async_engine(settings):
    engine = create_engine(settings)
    assert isinstance(engine, AsyncEngine)


def test_engine_url_contains_sqlite_path(settings):
    engine = create_engine(settings)
    url = str(engine.url)
    assert "sqlite" in url
    assert "db.sqlite" in url


def test_session_factory_returns_sessionmaker(settings):
    engine = create_engine(settings)
    factory = session_factory(engine)
    assert isinstance(factory, async_sessionmaker)


async def test_init_db_creates_tables(settings):
    engine = create_engine(settings)
    await init_db(engine)
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = {row[0] for row in result}
    assert "customer" in tables
    assert "item" in tables
    assert "order" in tables
    await engine.dispose()


async def test_foreign_keys_are_enabled(settings):
    engine = create_engine(settings)
    await init_db(engine)
    async with engine.connect() as conn:
        result = await conn.execute(text("PRAGMA foreign_keys"))
        value = result.scalar()
    assert value == 1
    await engine.dispose()
