"""Pure JS-bundle path-mining logic for inventory/build_inventory.py (mypy --strict clean)."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

_PATH_CHARS = r"[A-Za-z0-9_\-./]+"


def path_pattern(prefixes: Sequence[str]) -> re.Pattern[str]:
    alts = "|".join(re.escape(p) for p in prefixes)
    return re.compile(rf"""["'`]((?:{alts}){_PATH_CHARS})""")


def harvest_paths(chunks: Mapping[str, object], prefixes: Sequence[str]) -> list[str]:
    """Mine literal path strings under any of `prefixes` from JS bundle text."""
    if not prefixes:
        return []
    pattern = path_pattern(prefixes)
    return sorted({
        m.rstrip("/")
        for text in chunks.values() if isinstance(text, str)
        for m in pattern.findall(text)
    })
