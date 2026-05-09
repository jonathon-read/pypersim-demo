import uuid
from datetime import datetime, timezone

import pytest

from scripts.ingest_amazon import (
    UUID_NAMESPACE,
    _batched,
    _feature_id,
    _meta_to_rows,
    _review_id,
    _review_to_row,
    _to_float,
)


# ---------------------------------------------------------------------------
# _to_float
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value,expected", [
    ("3.14", 3.14),
    (42, 42.0),
    (1.5, 1.5),
    ("0", 0.0),
])
def test_to_float_valid(value, expected):
    assert _to_float(value) == expected


@pytest.mark.parametrize("value", [None, "", "abc", "N/A"])
def test_to_float_invalid_returns_none(value):
    assert _to_float(value) is None


# ---------------------------------------------------------------------------
# _feature_id / _review_id
# ---------------------------------------------------------------------------


def test_feature_id_is_deterministic():
    a = _feature_id("B001", 0)
    b = _feature_id("B001", 0)
    assert a == b


def test_feature_id_differs_by_index():
    assert _feature_id("B001", 0) != _feature_id("B001", 1)


def test_feature_id_is_valid_uuid():
    result = _feature_id("B001", 3)
    uuid.UUID(result)  # raises if invalid


def test_review_id_is_deterministic():
    a = _review_id("user1", "B001", 1700000000000)
    b = _review_id("user1", "B001", 1700000000000)
    assert a == b


def test_review_id_differs_by_user():
    assert _review_id("user1", "B001", 0) != _review_id("user2", "B001", 0)


def test_review_id_is_valid_uuid():
    result = _review_id("u", "B001", 1000)
    uuid.UUID(result)


# ---------------------------------------------------------------------------
# _meta_to_rows
# ---------------------------------------------------------------------------


def _valid_meta(**overrides):
    record = {
        "parent_asin": "B001",
        "title": "Organic Oats",
        "average_rating": 4.5,
        "rating_number": 100,
        "price": "9.99",
        "store": "Wholesome Co",
        "categories": ["Grocery", "Breakfast"],
        "details": {"Weight": "1 lb", "Brand": "Acme"},
        "features": ["Gluten-free", "Non-GMO"],
    }
    record.update(overrides)
    return record


def test_meta_to_rows_returns_empty_when_rating_too_low():
    record = _valid_meta(rating_number=5)
    assert _meta_to_rows(record) == {}


def test_meta_to_rows_returns_empty_when_no_price():
    record = _valid_meta(price=None)
    assert _meta_to_rows(record) == {}


def test_meta_to_rows_returns_empty_when_price_zero():
    record = _valid_meta(price=0)
    assert _meta_to_rows(record) == {}


def test_meta_to_rows_returns_all_keys_for_valid_record():
    rows = _meta_to_rows(_valid_meta())
    assert set(rows.keys()) == {"item", "item_category", "item_detail", "item_search", "item_feature"}


def test_meta_to_rows_deduplicates_categories():
    record = _valid_meta(categories=["Grocery", "Grocery", "Breakfast"])
    rows = _meta_to_rows(record)
    categories = [r["category"] for r in rows["item_category"]]
    assert len(categories) == len(set(categories))


def test_meta_to_rows_deduplicates_details():
    record = _valid_meta(details={"Weight": "1 lb", "Weight": "2 lb"})
    rows = _meta_to_rows(record)
    attrs = [r["attribute"] for r in rows["item_detail"]]
    assert len(attrs) == len(set(attrs))


def test_meta_to_rows_item_has_correct_asin():
    rows = _meta_to_rows(_valid_meta())
    assert rows["item"][0]["parent_asin"] == "B001"


def test_meta_to_rows_features_mapped():
    rows = _meta_to_rows(_valid_meta())
    assert len(rows["item_feature"]) == 2


# ---------------------------------------------------------------------------
# _review_to_row
# ---------------------------------------------------------------------------


def _valid_review(**overrides):
    record = {
        "review_id": "r1",
        "parent_asin": "B001",
        "user_id": "user1",
        "title": "Great oats",
        "text": "Loved them.",
        "rating": 5.0,
        "timestamp": 1700000000000,
        "verified_purchase": True,
        "helpful_vote": 3,
    }
    record.update(overrides)
    return record


def test_review_to_row_timestamp_is_utc_datetime():
    row = _review_to_row(_valid_review())
    assert isinstance(row["timestamp"], datetime)
    assert row["timestamp"].tzinfo == timezone.utc


def test_review_to_row_timestamp_value():
    row = _review_to_row(_valid_review(timestamp=1700000000000))
    expected = datetime.fromtimestamp(1700000000, tz=timezone.utc)
    assert row["timestamp"] == expected


def test_review_to_row_verified_purchase_coercion():
    assert _review_to_row(_valid_review(verified_purchase=True))["verified_purchase"] is True
    assert _review_to_row(_valid_review(verified_purchase=False))["verified_purchase"] is False


def test_review_to_row_helpful_vote_defaults_to_zero():
    record = _valid_review()
    del record["helpful_vote"]
    row = _review_to_row(record)
    assert row["helpful_vote"] == 0


# ---------------------------------------------------------------------------
# _batched
# ---------------------------------------------------------------------------


def test_batched_full_batches():
    result = list(_batched(range(6), 3))
    assert result == [[0, 1, 2], [3, 4, 5]]


def test_batched_partial_last_batch():
    result = list(_batched(range(5), 3))
    assert result == [[0, 1, 2], [3, 4]]


def test_batched_empty_input():
    assert list(_batched([], 3)) == []


def test_batched_single_element():
    assert list(_batched([42], 10)) == [[42]]


def test_batched_batch_size_one():
    result = list(_batched([1, 2, 3], 1))
    assert result == [[1], [2], [3]]
