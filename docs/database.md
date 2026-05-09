# Demo data model

The relational tables below live in SQLite (via SQLModel + aiosqlite). The vector tables — `item_search` (title) and `memory` — live in LanceDB; see [ADR 001](adr/001-database-and-vector-store.md) and [ADR 003](adr/003-drop-item-feature-vectorisation.md).

## Schema management

The SQLite schema is created on demand from the SQLModel metadata. `pypersim_demo.db.init_db()` calls `SQLModel.metadata.create_all` against the configured engine; the ingestion CLI and the agent both invoke it at startup, so there is no separate migration step. By default the database lives at `<cwd>/data/db.sqlite` — override with `PYPERSIM_DEMO_DATA_DIR=/path/to/dir`.

This is deliberate: the demo is a reference implementation with no production data to preserve. To pick up a schema change, delete the SQLite file and re-run ingestion. LanceDB tables are likewise schema-on-write, defined in `pypersim_demo/db/vectors.py` and applied via `ensure_tables()`.

## Entity relationship diagram

```mermaid
erDiagram
    
    CUSTOMER ||--o{ ORDER : "places"
    ITEM ||--o{ ITEM_CATEGORY : "has"
    ITEM ||--o{ ITEM_DETAIL : "has"
    ITEM ||--o{ ITEM_FEATURE : "has"
    ITEM ||--o{ REVIEW : "has"
    ORDER ||--|{ ORDER_LINE : "contains"
    ORDER_LINE ||--|| ITEM : "corresponds to"
    
    
    CUSTOMER {
        string customer_id PK
        string name "UNIQUE"
    }

    ITEM {
        string parent_asin PK
        string title "searchable (vectorized)"
        float average_rating
        int rating_number
        float price?
        string store?
    }

    ITEM_CATEGORY {
        string category PK
        string parent_asin PK,FK
    }

    ITEM_DETAIL {
        string parent_asin PK,FK
        string attribute PK
        string value
    }

    ITEM_FEATURE {
        string feature_id PK
        string parent_asin FK
        string feature
    }

    MEMORY["MEMORY (LanceDB)"] {
        string memory_id PK
        string content "searchable (vectorized)"
        vector content_vector "dim:384"
        string memory_type "preference | fact | complaint | other"
        datetime created_at
    }

    ORDER {
        string order_id PK
        string customer_id FK
        string status "draft | confirmed"
        date order_date
        date delivery_date
    }

    ORDER_LINE {
        string order_id PK,FK
        string parent_asin PK,FK
        int quantity
        float unit_price
    }

    REVIEW {
        string review_id PK
        string parent_asin FK
        string title
        string text
        float rating
        string user_id
        datetime timestamp
        boolean verified_purchase
        int helpful_vote
    }

```
