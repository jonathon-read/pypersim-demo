# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_core.py

# Run a single test by name
uv run pytest tests/test_core.py::test_error_to_dict_keys

# Lint and format
uv run ruff check src tests
uv run ruff format src tests

# Type-check
uv run mypy src
```

All tests are async (`asyncio_mode = "auto"` in pyproject.toml) — no `@pytest.mark.asyncio` needed.

## Architecture

This is a reference e-commerce customer support agent (groceries domain, Amazon Reviews 2023 dataset). The intended runtime is Google ADK, but only the data and tool layers are implemented so far.

### Two backing stores, one context object

`AppContext` (`context.py`) carries an async SQLAlchemy session and a LanceDB async connection into every tool call:

- **SQLite** via SQLModel + aiosqlite — customers, items, item details/categories/features, reviews, orders, order lines, and runtime tables (conversations, messages, memory records) created by the live agent.
- **LanceDB** (embedded) — two vector tables: `item_search` (item titles, 384-dim) and `memory` (customer memory content, 384-dim). Both use `all-MiniLM-L6-v2` via `sentence-transformers`.

`db/engine.py` provides `create_engine`, `session_factory`, and `init_db` (schema-on-demand, no migrations). `db/vectors.py` provides `connect`, `ensure_tables`, and table accessors. The database lives at `./data/` by default; override with `PYPERSIM_DEMO_DATA_DIR`.

### Tool registration pattern

`tools/_core.py` exports `make_tool_registry()`, which returns a pair of callables:
- `tool_factory` — a decorator that registers factory functions
- `build_registered_tools(ctx)` — instantiates all registered factories with an `AppContext` and returns `{fn.__name__: fn}`

Each domain module (e.g., `tools/assortment.py`) decorates its factory with `tool_factory` to self-register. This keeps tool wiring implicit; adding a new tool only requires decorating its factory in the right module.

### Service layer

`db/services/` contains async functions that accept `AppContext` and return typed results (Pydantic models from `schemas/`). Services raise `DatabaseServicesError` (code + message) on expected failures; `tools/_core.py` provides `error_to_dict` to convert these into a standard `{"result": "ERROR", "code": ..., "message": ...}` dict for the agent.

### Planned agent structure

The agent is a two-tier orchestrator + sub-agents (see `docs/architecture.md`). Sub-agents are exposed to the orchestrator as tools. All tool domains (assortment, customer, order) are planned but only `search_items` in the assortment service is currently implemented.
