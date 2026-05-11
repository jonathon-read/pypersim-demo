from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pypersim_demo.context import AppContext
from pypersim_demo.db.models import ItemDetail
from pypersim_demo.db.services._errors import DatabaseServicesError
from pypersim_demo.db.services.assortment import get_item, search_items
from pypersim_demo.schemas.assortment import ItemAttribute, ItemDetailResponse, ItemSearchResult


def _make_row(**overrides):
    row = {
        "parent_asin": "B001",
        "title": "Organic Oats",
        "price": 9.99,
        "average_rating": 4.5,
        "rating_number": 100,
    }
    row.update(overrides)
    return row


def _make_ctx():
    ctx = MagicMock(spec=AppContext)
    ctx.lance_conn = MagicMock()
    return ctx


def _make_rdb_ctx(
    item=None,
    categories=(),
    details=(),
    features=(),
):
    ctx = MagicMock(spec=AppContext)

    def _scalar_result(value):
        r = MagicMock()
        r.scalar_one_or_none.return_value = value
        return r

    def _scalars_result(values):
        r = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = list(values)
        r.scalars.return_value = scalars
        return r

    def _scalars_iter_result(rows):
        scalars_mock = MagicMock()
        scalars_mock.__iter__ = MagicMock(return_value=iter(rows))
        r = MagicMock()
        r.scalars.return_value = scalars_mock
        return r

    execute_results = [
        _scalar_result(item),
        _scalars_result(categories),
        _scalars_iter_result(details),
        _scalars_result(features),
    ]
    ctx.rdb_session = MagicMock()
    ctx.rdb_session.execute = AsyncMock(side_effect=execute_results)
    return ctx


def _make_item(**overrides):
    defaults = dict(
        parent_asin="B001",
        title="Organic Oats",
        average_rating=4.5,
        rating_number=120,
        price=9.99,
        store="OatsCo",
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_detail(attribute, value, parent_asin="B001"):
    d = MagicMock(spec=ItemDetail)
    d.attribute = attribute
    d.value = value
    return d


def _make_table_mock(rows):
    query = MagicMock()
    query.limit.return_value = query
    query.to_list = AsyncMock(return_value=rows)

    table = AsyncMock()
    table.search = AsyncMock(return_value=query)
    return table, query


async def test_search_items_returns_item_search_results():
    rows = [_make_row(), _make_row(parent_asin="B002", title="Steel Cut Oats")]
    table, _ = _make_table_mock(rows)

    with patch("pypersim_demo.db.services.assortment.item_search_table", return_value=table):
        results = await search_items(_make_ctx(), query="oats")

    assert len(results) == 2
    assert all(isinstance(r, ItemSearchResult) for r in results)
    assert results[0].parent_asin == "B001"
    assert results[1].parent_asin == "B002"


async def test_search_items_empty_results():
    table, _ = _make_table_mock([])

    with patch("pypersim_demo.db.services.assortment.item_search_table", return_value=table):
        results = await search_items(_make_ctx(), query="nothing")

    assert results == []


async def test_search_items_passes_query_to_search():
    table, query = _make_table_mock([])

    with patch("pypersim_demo.db.services.assortment.item_search_table", return_value=table):
        await search_items(_make_ctx(), query="granola bars")

    table.search.assert_awaited_once_with("granola bars")


async def test_search_items_passes_limit():
    table, query = _make_table_mock([])

    with patch("pypersim_demo.db.services.assortment.item_search_table", return_value=table):
        await search_items(_make_ctx(), query="oats", limit=5)

    query.limit.assert_called_once_with(5)


async def test_search_items_default_limit_is_10():
    table, query = _make_table_mock([])

    with patch("pypersim_demo.db.services.assortment.item_search_table", return_value=table):
        await search_items(_make_ctx(), query="oats")

    query.limit.assert_called_once_with(10)


async def test_search_items_uses_lance_conn_from_context():
    ctx = _make_ctx()
    table, _ = _make_table_mock([])

    with patch(
        "pypersim_demo.db.services.assortment.item_search_table", return_value=table
    ) as mock_item_search_table:
        await search_items(ctx, query="oats")

    mock_item_search_table.assert_awaited_once_with(ctx.lance_conn)


async def test_search_items_extra_fields_in_row_are_ignored():
    row = _make_row(vector=[0.1, 0.2], irrelevant_field="ignore me")
    table, _ = _make_table_mock([row])

    with patch("pypersim_demo.db.services.assortment.item_search_table", return_value=table):
        results = await search_items(_make_ctx(), query="oats")

    assert len(results) == 1
    assert not hasattr(results[0], "vector")


# ---------------------------------------------------------------------------
# get_item
# ---------------------------------------------------------------------------


async def test_get_item_returns_item_detail_response():
    item = _make_item()
    ctx = _make_rdb_ctx(item=item, categories=["Breakfast", "Cereals"])

    result = await get_item(ctx, "B001")

    assert isinstance(result, ItemDetailResponse)


async def test_get_item_maps_item_fields():
    item = _make_item(
        parent_asin="B001",
        title="Organic Oats",
        average_rating=4.5,
        rating_number=120,
        price=9.99,
        store="OatsCo",
    )
    ctx = _make_rdb_ctx(item=item)

    result = await get_item(ctx, "B001")

    assert result.parent_asin == "B001"
    assert result.title == "Organic Oats"
    assert result.average_rating == 4.5
    assert result.rating_number == 120
    assert result.price == 9.99
    assert result.store == "OatsCo"


async def test_get_item_includes_categories():
    item = _make_item()
    ctx = _make_rdb_ctx(item=item, categories=["Breakfast", "Organic"])

    result = await get_item(ctx, "B001")

    assert result.categories == ["Breakfast", "Organic"]


async def test_get_item_includes_features():
    item = _make_item()
    ctx = _make_rdb_ctx(item=item, features=["Gluten free", "Non-GMO"])

    result = await get_item(ctx, "B001")

    assert result.features == ["Gluten free", "Non-GMO"]


async def test_get_item_includes_details():
    item = _make_item()
    details = [_make_detail("Weight", "500g"), _make_detail("Origin", "Canada")]
    ctx = _make_rdb_ctx(item=item, details=details)

    result = await get_item(ctx, "B001")

    assert result.details == [
        ItemAttribute(attribute="Weight", value="500g"),
        ItemAttribute(attribute="Origin", value="Canada"),
    ]


async def test_get_item_empty_relations():
    item = _make_item()
    ctx = _make_rdb_ctx(item=item)

    result = await get_item(ctx, "B001")

    assert result.categories == []
    assert result.features == []
    assert result.details == []


async def test_get_item_nullable_price_and_store():
    item = _make_item(price=None, store=None)
    ctx = _make_rdb_ctx(item=item)

    result = await get_item(ctx, "B001")

    assert result.price is None
    assert result.store is None


async def test_get_item_not_found_raises_database_services_error():
    ctx = _make_rdb_ctx(item=None)

    with pytest.raises(DatabaseServicesError):
        await get_item(ctx, "MISSING")
