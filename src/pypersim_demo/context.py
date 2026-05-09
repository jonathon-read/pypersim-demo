from dataclasses import dataclass

import lancedb
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AppContext:
    rdb_session: AsyncSession
    lance_conn: lancedb.AsyncConnection
    order_id: str | None = None
