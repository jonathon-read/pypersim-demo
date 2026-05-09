# ADR 003: Drop item_feature vectorisation

**Status:** Accepted

## Context

The demo data directory totalled ~3.8 GB after ingesting ~400 K Amazon Grocery & Gourmet Food items, making the dataset impractical to bundle for distribution. The breakdown was:

| Table | Size |
|-------|------|
| `item_feature.lance` | 3.1 GB |
| `item_search.lance` | 813 MB |
| `memory.lance` | < 1 MB |
| `demo.sqlite` | ~300 MB |

The `item_feature` LanceDB table stored one 384-dim vector per feature bullet point. With an average of 5–8 features per item, this produced ~2–3 million vector rows.

Critically, no tool or query path ever read from `item_feature`. The `search_items` tool searches solely by item title via `item_search`. The feature vectors were generated and stored but never consumed.

## Decision

Drop the `item_feature` LanceDB table. Store item feature text as plain rows in a new SQLite `item_feature` table (no vectors).

- `ItemFeatureRow` LanceModel and `ITEM_FEATURE_TABLE` constant removed from `demo/app/vectors.py`
- `ItemFeature` SQLModel added to `demo/app/models.py` (created from metadata via `init_db()`)
- Ingestion script updated to write features to SQLite instead of LanceDB
- Schema diagram updated to remove `feature_vector` from `ITEM_FEATURE`

## Consequences

- `item_feature.lance` is no longer created on a fresh ingest; existing installs can delete it
- No tool behaviour changes — `item_feature` was never queried
- Feature text is preserved in SQLite for future use (e.g. full-text search or re-vectorisation with a different strategy)
- LanceDB storage drops from ~3.9 GB to ~0.8 GB for a full ingest
