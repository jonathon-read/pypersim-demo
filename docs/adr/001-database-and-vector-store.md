# ADR 001: Database and Vector Store

**Status:** Accepted

## Context

The demo agent's data model (see `../database.md`) combines:

- **Relational data** — customers, orders, order lines, items, conversation events, messages, tool calls
- **Vector data** — searchable embeddings for item titles, item features, and customer memory (all 384-dim)

Key constraints:
- Zero infrastructure — the demo must run without Docker or external services
- Async — the agent uses async Python throughout (pydantic-ai)
- Showcase vector retrieval — the implementation should demonstrate production-grade vector search patterns, not abstract them away
- Scale — several hundred thousand items; embeddings are generated at insertion time, queries are embedded on demand

## Decision

Use **SQLite + LanceDB** as a dual-store, with **SQLModel** as the ORM over SQLite.

### Store assignment

**SQLite (via SQLModel + aiosqlite)**

All relational tables: CUSTOMER, ORDER, ORDER_LINE, ITEM, ITEM_CATEGORY, ITEM_DETAIL, CONVERSATION, CONVERSATION_EVENT, MESSAGE, TOOL_CALL.

ITEM is kept in SQLite in full (including `title`) because it participates in relational joins with ORDER_LINE and ITEM_CATEGORY, and its text fields are passed directly as LLM context.

**LanceDB (embedded, async)**

The three vector tables: `item_search` (parent_asin, title, title_vector), `item_feature` (feature_id, parent_asin, feature, feature_vector), and `memory` (memory_id, conversation_id, content, content_vector, memory_type, created_at).

LanceDB holds the text alongside the vectors — text is required as retrieval output for LLM context generation. Vector search returns IDs and text; relational hydration (price, rating, order history) is done via a subsequent SQLite lookup.

ITEM is intentionally duplicated across both stores: SQLite holds the authoritative relational record; LanceDB holds a search-optimised projection `(parent_asin, title, title_vector)`.

### Embedding

Model: `all-MiniLM-L6-v2` from `sentence-transformers` (384-dim, local, no API key required).

Embeddings are generated:
- **At insertion time** for ITEM, ITEM_FEATURE, and MEMORY records
- **On demand** for user queries before vector search

### Schema management

The SQLite schema is created on demand from SQLModel metadata via `SQLModel.metadata.create_all` (called from `demo.app.db.init_db()` at startup). No migration tool is used: the demo has no production data to preserve, so schema changes are applied by deleting the SQLite file and re-ingesting. LanceDB tables are schema-on-write (defined by the PyArrow schema at table creation); changes are handled in application code.

## Considered alternatives

### PostgreSQL + pgvector
Production-grade, HNSW indexing, strong ecosystem. Rejected because it requires a running Postgres instance — violates the zero-infrastructure constraint.

### SQLite + sqlite-vec
Unified single-file solution. Rejected because sqlite-vec is nascent (2024) with limited community evidence at scale, and `aiosqlite` async is thread-pool based rather than truly async.

### DuckDB + VSS extension
Zero infrastructure, columnar store with HNSW support. Rejected because DuckDB is optimised for analytical read workloads; a conversational agent with per-turn writes is a transactional workload — a conceptual mismatch.

### SQLite + ChromaDB
ChromaDB's embedded mode is simple but abstracts too much of the vector search implementation. Rejected as insufficiently illustrative of vector retrieval patterns.

### SQLite + Qdrant (local mode)
Qdrant is an excellent production vector database. Its local/embedded mode exists but is not its primary use case and has less polish than LanceDB's embedded story.

## Packages

| Package | Role |
|---|---|
| `sqlmodel` | ORM + Pydantic model definitions for SQLite tables |
| `aiosqlite` | Async SQLite driver |
| `lancedb` | Embedded vector store for ITEM, ITEM_FEATURE, MEMORY |
| `pyarrow` | LanceDB dependency; used for table schema definition |
| `sentence-transformers` | Local 384-dim embedding generation |
