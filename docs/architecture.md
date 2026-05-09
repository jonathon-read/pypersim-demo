# Agent Architecture

## Overview

The demo agent uses a two-tier architecture: a single **orchestrator** that owns the conversation and delegates to specialist **sub-agents** for capabilities that require synthesis or multi-step reasoning. Simple, deterministic operations are handled by the orchestrator directly via tools.

This structure mirrors a production-like multi-agent deployment and serves as the primary test target for pypersim.

```
User
 │
 ▼
Orchestrator
 ├── [direct tools]
 │    ├── assortment: semantic_product_search, get_item,
 │    │               get_popular_items, get_product_recommendations
 │    ├── customer:   store_memory, search_memory,
 │    │               list_memories, get_memory_details, forget_memory
 │    └── order:      modify_order_line, clear_order, checkout,
 │                    get_order, get_order_history, initiate_return
 │
 ├── review_summariser ──────── get_item_reviews
 ├── dietary_assessor ───────── get_item
 ├── price_comparator ───────── semantic_product_search, get_item
 ├── preference_advisor ─────── search_memory, list_memories,
 │                              get_memory_details, semantic_product_search
 ├── substitution_suggester ─── semantic_product_search, get_item
 └── reorder_agent ──────────── get_order_history, modify_order_line
```

Sub-agents are exposed to the orchestrator as tools. Each sub-agent has its own system prompt scoped to its capability and holds only the tools it needs.

---

## Orchestrator

The orchestrator manages conversation state and customer session context. It decides whether a capability is a direct tool call or requires delegation to a sub-agent.

**Direct tool calls** are used when the operation is deterministic and requires no synthesis:
- Product discovery (search, popular, recommendations)
- Product detail lookup
- Customer memory read/write/delete/search
- Basket management and checkout
- Order history retrieval
- Return and refund initiation

**Delegation to sub-agents** is used when the capability requires reasoning across one or more tool results — for example, interpreting reviews, evaluating dietary suitability, or comparing alternatives.

---

## Sub-agents

### `review_summariser`
Synthesises customer reviews for a product into a structured summary of strengths, weaknesses, and recurring themes.

**Tools:** `get_item_reviews`

**When the orchestrator delegates:** User asks for a review summary, asks what customers say about a product, or wants signals beyond the raw rating.

---

### `dietary_assessor`
Evaluates a product's suitability for a stated dietary requirement based on its listed features and attributes. Always qualifies its assessment with advice to verify against the physical product label.

**Tools:** `get_item`

**When the orchestrator delegates:** User states a dietary requirement and asks whether a specific product is suitable.

---

### `price_comparator`
Finds products similar to a given item and compares them by price and rating to help the user make a value judgement.

**Tools:** `semantic_product_search`, `get_item`

**When the orchestrator delegates:** User asks to compare prices, find a cheaper alternative, or assess value for money relative to a specific product.

---

### `preference_advisor`
Proactively recommends products based on the customer's stored preferences and the current conversation context. Takes initiative rather than responding to an explicit product query.

**Tools:** `search_memory`, `list_memories`, `get_memory_details`, `semantic_product_search`

**When the orchestrator delegates:** Orchestrator judges that a proactive suggestion is appropriate given the customer's known preferences and the current topic.

---

### `substitution_suggester`
Proposes alternatives from the catalogue when a user is dissatisfied with a product or no suitable match could be found. Explains why each substitute is a reasonable match given the user's stated needs.

**Tools:** `semantic_product_search`, `get_item`

**When the orchestrator delegates:** User expresses dissatisfaction with a product, asks for something different, or a prior search returned no useful results.

---

### `reorder_agent`
Rebuilds a previous order into the current basket, allowing the user to review and adjust before checkout.

**Tools:** `get_order_history`, `modify_order_line`

**When the orchestrator delegates:** User asks to reorder a past purchase or asks the agent to recreate a previous basket.

---

## Tool inventory

Tools are grouped by domain. Sub-agent tool access is noted where a tool is shared with the orchestrator.

### Assortment

| Tool | Status | Used by |
|---|---|---|
| `semantic_product_search` | Planned | Orchestrator, `price_comparator`, `preference_advisor`, `substitution_suggester` |
| `get_item` | Planned | Orchestrator, `dietary_assessor`, `price_comparator`, `substitution_suggester` |
| `get_item_reviews` | Planned | `review_summariser` |
| `get_popular_items` | Planned | Orchestrator |
| `get_product_recommendations` | Planned | Orchestrator |

### Customer

| Tool | Status | Used by |
|---|---|---|
| `list_memories` | Planned | Orchestrator, `preference_advisor` |
| `get_memory_details` | Planned | Orchestrator, `preference_advisor` |
| `forget_memory` | Planned | Orchestrator |
| `store_memory` | Planned | Orchestrator |
| `search_memory` | Planned | Orchestrator, `preference_advisor` |

### Order

| Tool | Status | Used by |
|---|---|---|
| `modify_order_line` | Planned | Orchestrator, `reorder_agent` |
| `clear_order` | Planned | Orchestrator |
| `checkout` | Planned | Orchestrator |
| `get_order` | Planned | Orchestrator |
| `get_order_history` | Planned | Orchestrator, `reorder_agent` |
| `initiate_return` | Planned | Orchestrator |

---

## Data layer

All tools read from and write to two backing stores accessed via `AppContext`:

- **SQLite** (via SQLModel + aiosqlite) — customers, items, item details, item features, reviews, orders, order lines, conversations, conversation events, messages, tool calls, customer memory records.
- **LanceDB** (embedded, async) — two vector tables: `item_search` (product titles, 384-dim) and `memory` (memory content, 384-dim). Embeddings are generated locally using `all-MiniLM-L6-v2`.

`AppContext` is injected into every tool call and carries the async SQLAlchemy session and LanceDB connection for the current request.

---

## Capability coverage

| Capability | Realised by |
|---|---|
| Semantic product search | `semantic_product_search` (orchestrator) |
| What's popular | `get_popular_items` (orchestrator) |
| Product recommendations | `get_product_recommendations` (orchestrator) |
| Substitution suggester | `substitution_suggester` sub-agent |
| Product detail | `get_item` (orchestrator) |
| Review summariser | `review_summariser` sub-agent |
| Dietary assessor | `dietary_assessor` sub-agent |
| Price comparator | `price_comparator` sub-agent |
| Customer memory | `store_memory`, `search_memory`, `list_memories`, `get_memory_details`, `forget_memory` (orchestrator) |
| Preference-aware recommendations | `preference_advisor` sub-agent |
| Basket management | `modify_order_line`, `clear_order` (orchestrator) — requires customer registration |
| Checkout | `checkout` (orchestrator) |
| Order detail | `get_order` (orchestrator) |
| Order history | `get_order_history` (orchestrator) |
| Reorder | `reorder_agent` sub-agent |
| Return and refund initiator | `initiate_return` (orchestrator) |
