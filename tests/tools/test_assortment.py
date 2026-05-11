from unittest.mock import AsyncMock, MagicMock, patch

from pypersim_demo.context import AppContext, set_ctx
from pypersim_demo.db.services import DatabaseServicesError
from pypersim_demo.schemas.assortment import ItemDetailResponse, ErrorResponse
from pypersim_demo.tools.assortment import get_item


def _make_ctx():
    return MagicMock(spec=AppContext)


def _make_item_detail(**overrides):
    defaults = dict(
        parent_asin="B001",
        title="Organic Oats",
        price=9.99,
        average_rating=4.5,
        rating_number=120,
        store="OatsCo",
        categories=["Breakfast"],
        features=["Gluten free"],
        details=[],
    )
    defaults.update(overrides)
    return ItemDetailResponse(**defaults)


async def test_get_item_returns_item_detail_response():
    ctx = _make_ctx()
    set_ctx(ctx)
    detail = _make_item_detail()

    with patch("pypersim_demo.tools.assortment._get_item", AsyncMock(return_value=detail)):
        result = await get_item(parent_asin="B001")

    assert result == detail


async def test_get_item_error_returns_error_response():
    ctx = _make_ctx()
    set_ctx(ctx)

    with patch(
        "pypersim_demo.tools.assortment._get_item",
        AsyncMock(side_effect=DatabaseServicesError("parent_asin 'X' not found")),
    ):
        result = await get_item(parent_asin="X")

    assert isinstance(result, ErrorResponse)


async def test_get_item_error_message_is_preserved():
    ctx = _make_ctx()
    set_ctx(ctx)

    with patch(
        "pypersim_demo.tools.assortment._get_item",
        AsyncMock(side_effect=DatabaseServicesError("parent_asin 'X' not found")),
    ):
        result = await get_item(parent_asin="X")

    assert "not found" in result.error


async def test_get_item_passes_parent_asin_to_service():
    ctx = _make_ctx()
    set_ctx(ctx)
    mock = AsyncMock(return_value=_make_item_detail())

    with patch("pypersim_demo.tools.assortment._get_item", mock):
        await get_item(parent_asin="B999")

    mock.assert_awaited_once_with(ctx, "B999")
