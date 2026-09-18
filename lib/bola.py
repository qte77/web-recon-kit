"""Pure resource-id extraction for runners/r3_bola.py (mypy --strict clean)."""
from __future__ import annotations


def extract_ids(data: object, key: str, id_field: str = "id") -> list[str]:
    """Walk a (possibly dotted) key to a list of items, then pull `id_field` off each."""
    node: object = data
    for part in key.split("."):
        if not isinstance(node, dict):
            return []
        node = node.get(part)
    if not isinstance(node, list):
        return []
    return [str(item[id_field]) for item in node if isinstance(item, dict) and id_field in item]
