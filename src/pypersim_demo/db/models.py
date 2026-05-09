import uuid
from datetime import date, datetime

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def _new_uuid4_str() -> str:
    return str(uuid.uuid4())


class Customer(SQLModel, table=True):
    __tablename__ = "customer"  # type: ignore[assignment]
    __table_args__ = (UniqueConstraint("name", name="uq_name"),)  # type: ignore[assignment]

    customer_id: str = Field(default_factory=_new_uuid4_str, primary_key=True)
    name: str


class Item(SQLModel, table=True):
    __tablename__ = "item"  # type: ignore[assignment]

    parent_asin: str = Field(primary_key=True)
    title: str
    average_rating: float
    rating_number: int
    price: float | None = None
    store: str | None = None


class ItemCategory(SQLModel, table=True):
    __tablename__ = "item_category"  # type: ignore[assignment]

    category: str = Field(primary_key=True)
    parent_asin: str = Field(primary_key=True, foreign_key="item.parent_asin")


class ItemDetail(SQLModel, table=True):
    __tablename__ = "item_detail"  # type: ignore[assignment]

    parent_asin: str = Field(primary_key=True, foreign_key="item.parent_asin")
    attribute: str = Field(primary_key=True)
    value: str


class ItemFeature(SQLModel, table=True):
    __tablename__ = "item_feature"  # type: ignore[assignment]

    feature_id: str = Field(primary_key=True)
    parent_asin: str = Field(foreign_key="item.parent_asin", index=True)
    feature: str


class Review(SQLModel, table=True):
    __tablename__ = "review"  # type: ignore[assignment]

    review_id: str = Field(primary_key=True)
    parent_asin: str = Field(foreign_key="item.parent_asin")
    title: str
    text: str
    rating: float
    user_id: str
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    verified_purchase: bool
    helpful_vote: int


class Order(SQLModel, table=True):
    __tablename__ = "order"  # type: ignore[assignment]

    order_id: str = Field(primary_key=True)
    customer_id: str = Field(foreign_key="customer.customer_id")
    status: str = Field(default="draft")  # "draft" | "confirmed"
    order_date: date
    delivery_date: date


class OrderLine(SQLModel, table=True):
    __tablename__ = "order_line"  # type: ignore[assignment]

    order_id: str = Field(primary_key=True, foreign_key="order.order_id")
    parent_asin: str = Field(primary_key=True, foreign_key="item.parent_asin")
    quantity: int
    unit_price: float
