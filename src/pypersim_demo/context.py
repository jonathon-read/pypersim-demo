from contextvars import ContextVar
from dataclasses import dataclass

import lancedb
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AppContext:
    rdb_session: AsyncSession
    lance_conn: lancedb.AsyncConnection
    customer_id: str | None = None
    order_id: str | None = None

    async def close(self) -> None:
        await self.rdb_session.close()


class _CtxNotSet: ...


_CTX_NOT_SET = _CtxNotSet()

_app_context: ContextVar[AppContext | _CtxNotSet] = ContextVar(
    "app_context", default=_CTX_NOT_SET
)


def get_ctx() -> AppContext:
    ctx = _app_context.get()
    if isinstance(ctx, _CtxNotSet):
        raise RuntimeError(
            "AppContext not set for this task. "
            "Ensure before_agent_callback is configured on the Agent."
        )
    return ctx


def set_ctx(ctx: AppContext) -> None:
    _app_context.set(ctx)
