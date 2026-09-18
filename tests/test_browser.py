"""Tests for lib.browser's optional-import guard (no real polyfetch_scrape needed)."""
import sys
import types
from typing import cast

import pytest

from lib.browser import require_render_session


def test_require_render_session_exits_2_with_actionable_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setitem(sys.modules, "polyfetch_scrape", None)

    with pytest.raises(SystemExit) as excinfo:
        require_render_session()

    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "uv sync --extra browser" in err
    assert "patchright install chromium" in err
    assert "musllinux" in err


def test_require_render_session_returns_the_real_entry_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    fake = types.ModuleType("polyfetch_scrape")
    fake.render_session = sentinel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "polyfetch_scrape", fake)

    assert require_render_session() is cast(object, sentinel)
