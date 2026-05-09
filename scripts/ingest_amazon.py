"""Amazon Reviews 2023 (Grocery & Gourmet Food) ingestion CLI.

The SQLite schema is created on demand from the SQLModel metadata; no
migration step is required. Source files are cached under
`pypersim.paths.get_cache_dir() / "amazon_reviews_2023"` and downloaded on
demand from the McAuley Lab dataset mirror.
"""

from __future__ import annotations

import asyncio
import gzip
import os
import uuid
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import orjson
import typer
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import col
from tqdm import tqdm

from pypersim_demo.config import Settings
from pypersim_demo.db import create_engine, init_db, session_factory
from pypersim_demo.db.models import Item, ItemCategory, ItemDetail, ItemFeature, Review
from pypersim_demo.db.vectors import (
    ITEM_SEARCH_TABLE,
    ensure_tables,
)
from pypersim_demo.db.vectors import (
    connect as lance_connect,
)

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

META_URL = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/"
    "meta_categories/meta_Grocery_and_Gourmet_Food.jsonl.gz"
)
REVIEW_URL = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/"
    "review_categories/Grocery_and_Gourmet_Food.jsonl.gz"
)
META_FILENAME = "meta_Grocery_and_Gourmet_Food.jsonl.gz"
REVIEW_FILENAME = "Grocery_and_Gourmet_Food.jsonl.gz"

# Measured row counts — used to give tqdm a total without re-counting on every run.
META_TOTAL = 603_274
REVIEW_TOTAL = 14_318_520

UUID_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000001")

LANCE_BATCH_SIZE = 256


app = typer.Typer(help=__doc__, no_args_is_help=True, add_completion=False)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _meta_path(settings: Settings) -> Path:
    settings.ensure_dirs_exist()
    return settings.data_dir / META_FILENAME


def _reviews_path(settings: Settings) -> Path:
    settings.ensure_dirs_exist()
    return settings.data_dir / REVIEW_FILENAME


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _download_file(url: str, dest: Path) -> None:
    if dest.exists():
        typer.echo(f"already present: {dest}")
        return
    part = dest.with_suffix(dest.suffix + ".part")
    with httpx.Client(follow_redirects=True, timeout=None) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0)) or None
            with (
                part.open("wb") as f,
                tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=dest.name,
                ) as bar,
            ):
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
                    bar.update(len(chunk))
    part.rename(dest)


# ---------------------------------------------------------------------------
# JSONL streaming
# ---------------------------------------------------------------------------


def _iter_jsonl_gz(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rb") as f:
        for line in f:
            yield orjson.loads(line)


def _batched(iterable: Iterable[Any], n: int) -> Iterator[list[Any]]:
    batch: list[Any] = []
    for x in iterable:
        batch.append(x)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch


# ---------------------------------------------------------------------------
# Meta record → table rows
# ---------------------------------------------------------------------------


def _feature_id(parent_asin: str, index: int) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE, f"feature|{parent_asin}|{index}"))


def _review_id(user_id: str, parent_asin: str, timestamp_ms: int) -> str:
    return str(
        uuid.uuid5(UUID_NAMESPACE, f"review|{user_id}|{parent_asin}|{timestamp_ms}")
    )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _meta_to_rows(record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Split one meta record into rows for each destination table."""
    parent_asin = record["parent_asin"]
    store_raw = record.get("store")
    store = store_raw if store_raw else None

    item_row = {
        "parent_asin": parent_asin,
        "title": record.get("title", "") or "",
        "average_rating": float(record.get("average_rating") or 0.0),
        "rating_number": int(record.get("rating_number") or 0),
        "price": _to_float(record.get("price")),
        "store": store,
    }

    if item_row["rating_number"] <= 5 or not item_row["price"]:
        return {}

    seen_categories: set[str] = set()
    category_rows: list[dict[str, Any]] = []
    for category in record.get("categories") or []:
        if not category or category in seen_categories:
            continue
        seen_categories.add(category)
        category_rows.append({"category": category, "parent_asin": parent_asin})

    seen_attrs: set[str] = set()
    detail_rows: list[dict[str, Any]] = []
    for attribute, value in (record.get("details") or {}).items():
        if not attribute or attribute in seen_attrs:
            continue
        seen_attrs.add(attribute)
        detail_rows.append({
            "parent_asin": parent_asin,
            "attribute": str(attribute),
            "value": "" if value is None else str(value),
        })

    item_search_rows = [
        {
            "parent_asin": parent_asin,
            "title": item_row["title"],
            "price": item_row["price"],
            "average_rating": item_row["average_rating"],
            "rating_number": item_row["rating_number"],
        }
    ]

    feature_rows: list[dict[str, Any]] = []
    for i, feature in enumerate(record.get("features") or []):
        if not feature:
            continue
        feature_rows.append({
            "feature_id": _feature_id(parent_asin, i),
            "parent_asin": parent_asin,
            "feature": str(feature),
        })

    return {
        "item": [item_row],
        "item_category": category_rows,
        "item_detail": detail_rows,
        "item_search": item_search_rows,
        "item_feature": feature_rows,
    }


def _review_to_row(record: dict[str, Any]) -> dict[str, Any]:
    ts_ms = int(record["timestamp"])
    return {
        "review_id": _review_id(record["user_id"], record["parent_asin"], ts_ms),
        "parent_asin": record["parent_asin"],
        "title": record.get("title", "") or "",
        "text": record.get("text", "") or "",
        "rating": float(record.get("rating") or 0.0),
        "user_id": record["user_id"],
        "timestamp": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
        "verified_purchase": bool(record.get("verified_purchase", False)),
        "helpful_vote": int(record.get("helpful_vote") or 0),
    }


# ---------------------------------------------------------------------------
# Bulk insert helpers
# ---------------------------------------------------------------------------


async def _sqlite_insert_ignore(session, model, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    stmt = sqlite_insert(model).values(rows)
    stmt = stmt.on_conflict_do_nothing()
    await session.execute(stmt)


async def _lance_merge(table, rows: list[dict[str, Any]], key: str) -> None:
    if not rows:
        return
    await (
        table
        .merge_insert(key)
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute(rows)
    )


# ---------------------------------------------------------------------------
# items command
# ---------------------------------------------------------------------------


async def _ingest_items(
    settings: Settings,
    path: Path,
    batch_size: int,
    limit: int | None,
) -> None:
    engine = create_engine(settings)
    await init_db(engine)
    Session = session_factory(engine)
    conn = await lance_connect(settings)
    await ensure_tables(conn, settings)
    item_search = await conn.open_table(ITEM_SEARCH_TABLE)

    records = _iter_jsonl_gz(path)
    if limit is not None:
        records = (r for i, r in enumerate(records) if i < limit)
    total = limit if limit is not None else META_TOTAL

    bar = tqdm(total=total, desc="items", unit="rec")
    try:
        for batch in _batched(records, batch_size):
            split: dict[str, list[dict[str, Any]]] = {
                "item": [],
                "item_category": [],
                "item_detail": [],
                "item_search": [],
                "item_feature": [],
            }
            for record in batch:
                rows = _meta_to_rows(record)
                if not rows:
                    continue
                for k, v in rows.items():
                    split[k].extend(v)

            async with Session() as session:
                async with session.begin():
                    await _sqlite_insert_ignore(session, Item, split["item"])
                    await _sqlite_insert_ignore(
                        session, ItemCategory, split["item_category"]
                    )
                    await _sqlite_insert_ignore(
                        session, ItemDetail, split["item_detail"]
                    )
                    await _sqlite_insert_ignore(
                        session, ItemFeature, split["item_feature"]
                    )

            for chunk in _batched(split["item_search"], LANCE_BATCH_SIZE):
                await _lance_merge(item_search, chunk, key="parent_asin")

            bar.update(len(batch))
    finally:
        bar.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# reviews command
# ---------------------------------------------------------------------------


async def _ingest_reviews(
    settings: Settings,
    path: Path,
    batch_size: int,
    limit: int | None,
    min_helpful_votes: int,
) -> None:
    engine = create_engine(settings)
    await init_db(engine)
    Session = session_factory(engine)

    typer.echo("loading catalogue parent_asin set...")
    async with Session() as session:
        result = await session.execute(select(col(Item.parent_asin)))
        known_asins: set[str] = set(result.scalars().all())
    typer.echo(f"  {len(known_asins):,} items in catalogue")
    if not known_asins:
        typer.echo("catalogue is empty — run `items` first", err=True)
        raise typer.Exit(code=1)

    bar = tqdm(total=REVIEW_TOTAL, desc="reviews scanned", unit="rec")
    kept_bar = tqdm(desc="reviews kept", unit="rec")

    def _filtered() -> Iterator[dict[str, Any]]:
        kept = 0
        for record in _iter_jsonl_gz(path):
            bar.update(1)
            if int(record.get("helpful_vote") or 0) < min_helpful_votes:
                continue
            if record.get("parent_asin") not in known_asins:
                continue
            yield record
            kept += 1
            if limit is not None and kept >= limit:
                return

    try:
        for batch in _batched(_filtered(), batch_size):
            rows = [_review_to_row(r) for r in batch]
            async with Session() as session:
                async with session.begin():
                    await _sqlite_insert_ignore(session, Review, rows)
            kept_bar.update(len(rows))
    finally:
        bar.close()
        kept_bar.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# Typer commands
# ---------------------------------------------------------------------------


@app.command()
def download() -> None:
    """Download the meta and review .jsonl.gz files if missing."""
    settings = Settings()
    _download_file(META_URL, _meta_path(settings))
    _download_file(REVIEW_URL, _reviews_path(settings))


@app.command()
def items(
    batch_size: int = typer.Option(1000, "--batch-size"),
    limit: int | None = typer.Option(None, "--limit"),
) -> None:
    """Ingest item metadata into SQLite + LanceDB."""
    settings = Settings()
    asyncio.run(_ingest_items(settings, _meta_path(settings), batch_size, limit))


@app.command()
def reviews(
    batch_size: int = typer.Option(1000, "--batch-size"),
    limit: int | None = typer.Option(None, "--limit"),
    min_helpful_votes: int = typer.Option(5, "--min-helpful-votes"),
) -> None:
    """Ingest reviews (filtered by helpful_vote) into SQLite."""
    settings = Settings()
    asyncio.run(
        _ingest_reviews(
            settings, _reviews_path(settings), batch_size, limit, min_helpful_votes
        )
    )


@app.command(name="all")
def all_(
    batch_size: int = typer.Option(1000, "--batch-size"),
    limit: int | None = typer.Option(None, "--limit"),
    min_helpful_votes: int = typer.Option(5, "--min-helpful-votes"),
) -> None:
    """Run download → items → reviews."""
    settings = Settings()
    download()
    asyncio.run(_ingest_items(settings, _meta_path(settings), batch_size, limit))
    asyncio.run(
        _ingest_reviews(
            settings, _reviews_path(settings), batch_size, limit, min_helpful_votes
        )
    )


if __name__ == "__main__":
    app()
