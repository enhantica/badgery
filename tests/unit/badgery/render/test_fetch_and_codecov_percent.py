from __future__ import annotations

from urllib.error import URLError

import pytest

from badgery.badges import BadgeGenerator
from badgery.render import HTMLDashboardRenderer


def test_fetch_non_https_and_urllib_error(monkeypatch: pytest.MonkeyPatch):
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('r/x'))
    # Non-https returns None early
    assert r._fetch('http://example.com') is None

    # Patch urlopen to raise URLError
    class FakeResp:
        status = 200

        def read(self):  # pragma: no cover - not used
            _ = self
            return b''

    def raise_url_error(url, timeout=8.0):  # noqa: ARG001
        # Raise URLError with an exception instance as reason to avoid
        # string messages per TRY003
        raise URLError(OSError())

    monkeypatch.setattr('badgery.render.urlopen', raise_url_error)
    assert r._fetch('https://example.com/badge.svg') is None


def test_codecov_percent_chooses_last_and_rounds(monkeypatch: pytest.MonkeyPatch):
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('org/repo'))

    def fake_fetch(url: str, timeout: float = 8.0) -> str:  # noqa: ARG001
        # Two percents present, parser should pick the last
        return '<svg><text>74%</text><text>81.2%</text></svg>'

    monkeypatch.setattr(r, '_fetch', fake_fetch)
    expected = 81
    assert r._codecov_percent('dev') == expected
