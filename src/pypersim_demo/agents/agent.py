import asyncio
import logging
from collections.abc import Callable
from typing import Any

import lancedb
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from pypersim_demo.config import Settings
from pypersim_demo.context import AppContext, set_ctx
from pypersim_demo.db.engine import create_engine, init_db, session_factory
from pypersim_demo.db.vectors import connect as lance_connect
from pypersim_demo.db.vectors import ensure_tables
from pypersim_demo.tools.assortment import tools as assortment_tools

logger = logging.getLogger(__name__)


def _build_model(settings: Settings) -> BaseLlm:
    if settings.agent_model_provider == "google":
        return Gemini(model=settings.agent_model_name)
    return LiteLlm(model=settings.agent_model_name)


_instruction = """\
You are a customer support agent for an online grocery and gourmet food store. \
You help customers find products, understand what they are buying, and make good \
purchasing decisions.

## What you can do

**Product search** — use `semantic_product_search` when the customer describes a \
need in natural language and you do not already have a product identifier. Always \
judge the results yourself: the tool returns the closest semantic matches but some \
may not fit the customer's actual need. Discard results that are clearly wrong and \
tell the customer if nothing useful came back.

**Product detail** — use `get_item` when you have a `parent_asin` and need full \
information: title, price, rating, store, features, and structured attributes. \
Call this after a search when the customer wants to know more about a specific \
result, or when answering questions about a known product.

## Tool sequencing

- If a customer names a product but gives no identifier, search first, then call \
  `get_item` on the best match.
- Use `parent_asin` values from search results or conversation history — never \
  construct or guess one from a product name.
- Only fetch details for products the customer has expressed interest in; do not \
  pre-fetch speculatively.

## Tone and style

- Be concise and factual. The customer is here to shop, not to read essays.
- When presenting search results, lead with the most relevant options and include \
  price and rating so the customer can compare at a glance.
- If a product has no price listed, say so explicitly — do not omit it silently.
- For dietary or allergy questions, use the features and details from `get_item` \
  to give a best-effort answer, but always remind the customer to verify against \
  the physical product label before purchasing.
"""

_TOOL_REMINDER_THRESHOLD = 10  # inject after this many messages in history
_TOOL_REMINDER = types.Content(
    role="model",
    parts=[types.Part(text=(
        "I should use my tools (semantic_product_search, get_item) to look up "
        "real product data rather than relying on memory."
    ))],
)

_settings = Settings()
_engine: AsyncEngine | None = None
_lance_conn: lancedb.AsyncConnection | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None
_init_lock = asyncio.Lock()
_sessions: dict[str, AppContext] = {}


async def _ensure_process_resources() -> None:
    global _engine, _lance_conn, _session_maker
    if _session_maker is not None:
        return
    async with _init_lock:
        if _session_maker is not None:
            return
        _engine = create_engine(_settings)
        await init_db(_engine)
        _lance_conn = await lance_connect(_settings)
        await ensure_tables(_lance_conn, _settings)
        _session_maker = session_factory(_engine)
        logger.info("Process-level DB resources initialized")


def _before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
    contents = llm_request.contents
    if contents and len(contents) >= _TOOL_REMINDER_THRESHOLD:
        contents.insert(-1, _TOOL_REMINDER)


async def _before_agent_callback(callback_context: CallbackContext) -> None:
    session_id = callback_context.session.id
    await _ensure_process_resources()
    assert _session_maker is not None
    assert _lance_conn is not None
    if session_id not in _sessions:
        _sessions[session_id] = AppContext(
            rdb_session=_session_maker(),
            lance_conn=_lance_conn,
        )
    set_ctx(_sessions[session_id])


async def _after_agent_callback(callback_context: CallbackContext) -> None:
    session_id = callback_context.session.id
    app_ctx = _sessions.pop(session_id, None)
    if app_ctx is not None:
        await app_ctx.close()
        logger.debug("Closed DB session for ADK session %s", session_id)


_tools: list[Callable[..., Any]] = list(assortment_tools)  # type: ignore[arg-type]

root_agent = Agent(
    model=_build_model(_settings),
    name="root",
    instruction=_instruction,
    tools=_tools,  # type: ignore[arg-type]
    before_model_callback=_before_model_callback,
    before_agent_callback=_before_agent_callback,
    after_agent_callback=_after_agent_callback,
)
