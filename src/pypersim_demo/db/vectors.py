from datetime import datetime
from functools import lru_cache

import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from lancedb.table import AsyncTable

from pypersim_demo.config import Settings

ITEM_SEARCH_TABLE = "item_search"
MEMORY_TABLE = "memory"


@lru_cache(maxsize=4)
def _embedder(model_name: str):  # type: ignore[no-untyped-def]
    return get_registry().get("sentence-transformers").create(name=model_name)


def _schemas(model_name: str) -> dict[str, type[LanceModel]]:
    func = _embedder(model_name)

    class ItemSearchRow(LanceModel):
        parent_asin: str
        title: str = func.SourceField()
        title_vector: Vector(func.ndims()) = func.VectorField()  # type: ignore[valid-type]
        price: float
        average_rating: float
        rating_number: int

    class MemoryRow(LanceModel):
        memory_id: str
        conversation_id: str
        content: str = func.SourceField()
        content_vector: Vector(func.ndims()) = func.VectorField()  # type: ignore[valid-type]
        memory_type: str
        created_at: datetime

    return {
        ITEM_SEARCH_TABLE: ItemSearchRow,
        MEMORY_TABLE: MemoryRow,
    }


async def connect(settings: Settings) -> lancedb.AsyncConnection:
    settings.ensure_dirs_exist()
    return await lancedb.connect_async(str(settings.lance_dir))


async def ensure_tables(conn: lancedb.AsyncConnection, settings: Settings) -> None:
    for name, schema in _schemas(settings.embedding_model).items():
        await conn.create_table(name, schema=schema, exist_ok=True)


async def item_search_table(conn: lancedb.AsyncConnection) -> AsyncTable:
    return await conn.open_table(ITEM_SEARCH_TABLE)


async def memory_table(conn: lancedb.AsyncConnection) -> AsyncTable:
    return await conn.open_table(MEMORY_TABLE)
