# ADR 002: ITEM_DETAIL storage representation

**Status:** Deferred

## Context

The `ITEM_DETAIL` table models variable product attributes (e.g. dimensions, materials, specs) using an Entity-Attribute-Value (EAV) pattern. EAV works as a conceptual model but has known drawbacks at the physical layer: no type safety on values, and attribute-level queries require awkward row-pivoting.

A JSON/document column is the natural alternative — simpler to work with in application code — but the query and indexing support varies significantly by database engine.

The database has not yet been selected. It must be a hybrid relational-vector store to support the vectorised search on `ITEM`, `ITEM_FEATURE`, and `MEMORY`. The right physical representation for `ITEM_DETAIL` depends on what that store natively supports.

## Decision

Deferred until the database is chosen.

## Options to revisit

- **JSON column** — straightforward if the chosen DB supports queryable JSON (e.g. JSONB in Postgres, JSON in MySQL/MariaDB, native documents in a hybrid store). Eliminates the join; loses attribute-level filtering unless the DB provides JSON indexing.
- **EAV table** (current diagram) — portable across any relational engine; query-hostile for attribute filtering but acceptable if details are only ever read as a full set per item.
- **Native document storage** — if the chosen hybrid store has a document model, `ITEM_DETAIL` may collapse into the item record entirely.

## Consequences

When the database is selected, revisit this decision and update the schema diagram and this ADR accordingly.
