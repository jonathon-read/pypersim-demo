from dataclasses import dataclass

import lancedb
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AppContext:
    rdb_session: AsyncSession
    lance_conn: lancedb.AsyncConnection
    customer_id: str | None = None
    order_id: str | None = None
