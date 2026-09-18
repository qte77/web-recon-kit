"""Tests for lib.bola's resource-id extraction (pure, no network)."""
import pytest

from lib.bola import extract_ids


def test_extract_ids_flat_collection_default_id_field() -> None:
    data = {"widgets": [{"id": 1}, {"id": "b"}]}
    assert extract_ids(data, "widgets") == ["1", "b"]


def test_extract_ids_follows_dotted_key() -> None:
    data = {"data": {"result": {"items": [{"id": 7}]}}}
    assert extract_ids(data, "data.result.items") == ["7"]


def test_extract_ids_uses_configured_id_field() -> None:
    data = {"items": [{"uuid": "u-1", "id": 9}]}
    assert extract_ids(data, "items", id_field="uuid") == ["u-1"]


@pytest.mark.parametrize(
    ("data", "key"),
    [
        (None, "items"),
        ({"items": {}}, "items"),
        ({"data": [1]}, "data.items"),
        ({"items": [{"other": 1}]}, "items"),
    ],
)
def test_extract_ids_empty_when_shape_mismatches(data: object, key: str) -> None:
    assert extract_ids(data, key) == []
