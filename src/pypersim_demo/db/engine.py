from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from pypersim_demo.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create an async SQLite engine with foreign key enforcement enabled."""
    settings.ensure_dirs_exist()
    url = f"sqlite+aiosqlite:///{settings.sqlite_path}"
    engine = create_async_engine(url, future=True)

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return a session factory bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine) -> None:
    """Create all SQLModel tables that do not yet exist in the database."""
    import pypersim_demo.db.models  # noqa: F401 — registers models with SQLModel.metadata

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
