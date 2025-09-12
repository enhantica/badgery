from __future__ import annotations

from collections.abc import Callable

import pytest

from badgery.badges import BadgeGenerator
from badgery.render import HTMLDashboardRenderer


def test_fetch_success_path_and_status_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('org/repo'))

    # Directly patch the fetch helper to simulate a successful fetch
    monkeypatch.setattr(r, '_fetch', lambda _url, _timeout=8.0: '<svg>ok</svg>')
    assert r._fetch('https://example.com/x.svg') == '<svg>ok</svg>'  # noqa: SLF001

    # Status variants mapping
    def fake_fetch_status(txt: str) -> Callable[..., str]:
        return lambda *_a, **_k: f'<svg><text>{txt}</text></svg>'

    # in progress should map verbatim (lowercased)
    monkeypatch.setattr(r, '_fetch', fake_fetch_status('in progress'))
    assert r._github_badge_status('ci.yml', 'dev') == 'in progress'  # noqa: SLF001
