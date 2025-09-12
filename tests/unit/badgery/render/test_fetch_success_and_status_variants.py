from __future__ import annotations

from badgery.badges import BadgeGenerator
from badgery.render import HTMLDashboardRenderer


def test_fetch_success_path_and_status_variants(monkeypatch):
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('org/repo'))

    # Provide a fake urlopen that returns 200 and bytes
    class DummyResp:
        def __init__(self, status: int, payload: bytes):
            self.status = status
            self._payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401
            return False

        def read(self):
            return self._payload

    monkeypatch.setattr(
        'badgery.render.urlopen', lambda url, timeout=8.0: DummyResp(200, b'<svg>ok</svg>')
    )
    assert r._fetch('https://example.com/x.svg') == '<svg>ok</svg>'

    # Status variants mapping
    def fake_fetch_status(txt: str):
        return lambda *_a, **_k: f'<svg><text>{txt}</text></svg>'

    # in progress should map verbatim (lowercased)
    monkeypatch.setattr(r, '_fetch', fake_fetch_status('in progress'))
    assert r._github_badge_status('ci.yml', 'dev') == 'in progress'
