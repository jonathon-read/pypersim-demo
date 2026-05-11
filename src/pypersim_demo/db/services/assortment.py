from pydantic import ValidationError
from sqlalchemy import select
from sqlmodel import col

from pypersim_demo.context import AppContext
from pypersim_demo.db.models import Item, ItemCategory, ItemDetail, ItemFeature
from pypersim_demo.db.services._errors import DatabaseServicesError
from pypersim_demo.db.vectors import item_search_table
from pypersim_demo.schemas.assortment import (
    ItemAttribute,
    ItemDetailResponse,
    ItemSearchResult,
)


async def get_item(ctx: AppContext, parent_asin: str):
    item_result = await ctx.rdb_session.execute(
        select(Item).where(col(Item.parent_asin) == parent_asin)
    )
    item = item_result.scalar_one_or_none()
    if item is None:
        raise DatabaseServicesError(f"parent_asin '{parent_asin}' not found")

    categories_result = await ctx.rdb_session.execute(
        select(col(ItemCategory.category)).where(
            col(ItemCategory.parent_asin) == parent_asin
        )
    )
    details_result = await ctx.rdb_session.execute(
        select(ItemDetail).where(col(ItemDetail.parent_asin) == parent_asin)
    )
    features_result = await ctx.rdb_session.execute(
        select(col(ItemFeature.feature)).where(
            col(ItemFeature.parent_asin) == parent_asin
        )
    )

    return ItemDetailResponse(
        parent_asin=item.parent_asin,
        title=item.title,
        price=item.price,
        average_rating=item.average_rating,
        rating_number=item.rating_number,
        store=item.store,
        categories=list(categories_result.scalars().all()),
        details=[
            ItemAttribute(attribute=detail.attribute, value=detail.value)
            for detail in details_result.scalars()
        ],
        features=list(features_result.scalars().all()),
    )


async def search_items(
    ctx: AppContext, query: str, limit: int = 10
) -> list[ItemSearchResult]:
    try:
        table = await item_search_table(ctx.lance_conn)
        rows = await (await table.search(query)).limit(limit).to_list()
        return [ItemSearchResult.model_validate(r) for r in rows]
    except (OSError, RuntimeError, ValidationError) as e:
        raise DatabaseServicesError(str(e)) from e
