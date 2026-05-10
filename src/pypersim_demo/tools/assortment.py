import logging
from collections.abc import Callable

from pypersim_demo.context import AppContext
from pypersim_demo.db.services import DatabaseServicesError
from pypersim_demo.db.services.assortment import get_item as _get_item, search_items
from pypersim_demo.schemas.assortment import (
    ErrorResponse,
    ItemDetailResponse,
    ItemSearchResponse,
    SemanticProductSearchResult,
)
from pypersim_demo.tools._core import make_tool_registry

logger = logging.getLogger(__name__)

_assortment_tool_factory, assortment_tools = make_tool_registry()


@_assortment_tool_factory
def _make_semantic_product_search(ctx: AppContext) -> Callable:
    async def semantic_product_search(
        query: str, limit: int = 10
    ) -> SemanticProductSearchResult:
        """
        Search the product catalogue using a natural-language query and return the
        closest-matching items ranked by semantic similarity.

        Use this tool when the customer describes what they want (e.g. "something
        for washing dishes", "a birthday gift for a 5-year-old") rather than naming
        a specific product. Prefer descriptive queries over single keywords — the
        more context in the query, the better the results.

        Results are approximate: similarity matching may surface loosely related
        items. Always verify that returned items make sense for the customer's need
        before presenting or recommending them.

        Args:
            query: Natural-language description of what the customer is looking for.
            limit: Maximum number of results to return (default 10).

        Returns:
            A list of matching items, each with parent_asin, title, price,
            average_rating, and rating_number. Returns an error dict on failure.
        """
        try:
            items = await search_items(ctx, query, limit)
            return ItemSearchResponse(items=items)
        except DatabaseServicesError as e:
            logging.error("search_items failed with %s", str(e))
            return ErrorResponse(error="database services error")

    return semantic_product_search


@_assortment_tool_factory
def _make_get_item(ctx: AppContext) -> Callable:
    async def get_item(parent_asin: str) -> ItemDetailResponse | ErrorResponse:
        """
        Retrieve full details for a single product by its parent ASIN.

        Use this tool when you need detailed information about a specific item
        that you already know the ASIN for — for example, after a semantic search
        has returned candidate ASINs and the customer wants to know more.

        Args:
            parent_asin: The product's parent ASIN identifier.

        Returns:
            Full item detail including title, price, rating, store, categories,
            features, and structured attributes. Returns an error response if
            the ASIN does not exist or on failure.
        """
        try:
            return await _get_item(ctx, parent_asin)
        except DatabaseServicesError as e:
            logger.error("get_item failed with %s", str(e))
            return ErrorResponse(error=str(e))

    return get_item
