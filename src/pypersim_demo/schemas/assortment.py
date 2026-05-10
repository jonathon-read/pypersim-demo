from pydantic import BaseModel, ConfigDict

from pypersim_demo.schemas._core import ErrorResponse


class ItemSearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    parent_asin: str
    title: str
    price: float
    average_rating: float
    rating_number: int


class ItemAttribute(BaseModel):
    attribute: str
    value: str


class Review(BaseModel):
    review_id: str
    title: str
    text: str
    rating: float
    user_id: str
    timestamp: str
    verified_purchase: bool
    helpful_vote: int


class ItemSearchResponse(BaseModel):
    items: list[ItemSearchResult]


class ItemDetailResponse(BaseModel):
    parent_asin: str
    title: str
    price: float | None
    average_rating: float
    rating_number: int
    store: str | None
    categories: list[str]
    features: list[str]
    details: list[ItemAttribute]


class ReviewsResponse(BaseModel):
    reviews: list[Review]


SemanticProductSearchResult = ItemSearchResponse | ErrorResponse
GetItemResult = ItemDetailResponse | ErrorResponse
GetItemReviewsResult = ReviewsResponse | ErrorResponse
