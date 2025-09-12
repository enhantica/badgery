from __future__ import annotations

from typing import Never

from badgery.badges import BadgeGenerator
from badgery.metrics import BaseMetric
from badgery.render import HTMLDashboardRenderer


class DummyMetric(BaseMetric):
    def read_value(self, path: str) -> Never:  # pragma: no cover - not used
        raise NotImplementedError

    def read_all(self, args: object) -> Never:  # pragma: no cover - not used
        raise NotImplementedError

    def badge(self, _value: object) -> str:  # pragma: no cover - not used
        _ = self
        return ''


def test_renderer_color_thresholds_and_complexity_grade() -> None:
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('r/x'))
    # _color_for_percent
    assert r._color_for_percent(95) == 'green'  # noqa: SLF001
    assert r._color_for_percent(76) == 'yellow-green'  # noqa: SLF001
    assert r._color_for_percent(61) == 'yellow'  # noqa: SLF001
    assert r._color_for_percent(41) == 'orange'  # noqa: SLF001
    assert r._color_for_percent(10) == 'red'  # noqa: SLF001
    assert r._color_for_percent(None) == 'gray'  # noqa: SLF001

    # _complexity_grade_color
    assert r._complexity_grade_color(3) == ('A', 'green')  # noqa: SLF001
    assert r._complexity_grade_color(8) == ('B', 'yellow-green')  # noqa: SLF001
    assert r._complexity_grade_color(15) == ('C', 'yellow')  # noqa: SLF001
    assert r._complexity_grade_color(30) == ('D', 'orange')  # noqa: SLF001
    assert r._complexity_grade_color(100) == ('F', 'red')  # noqa: SLF001
    assert r._complexity_grade_color(None) == ('?', 'gray')  # noqa: SLF001


def test_renderer_parses_svg_for_status_and_percent(monkeypatch: object) -> None:
    # Prepare a renderer with a dummy metric to access methods
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('r/x'))

    # Monkeypatch network fetch to deterministic SVGs
    def fake_fetch(url: str, timeout: float = 8.0) -> str:  # noqa: ARG001
        if 'badge.svg' in url and 'actions' in url:
            # Simulate GitHub workflow badge
            return '<svg><text>passing</text></svg>'
        if 'codecov' in url:
            # Simulate Codecov percent
            return '<svg><g><text>85%</text></g></svg>'
        if 'codefactor' in url:
            # Simulate CodeFactor letter
            return '<svg><g><text>A</text></g></svg>'
        return ''

    monkeypatch.setattr(r, '_fetch', fake_fetch)

    # GitHub status
    assert r._github_badge_status('ci.yml', 'main') == 'passed'  # noqa: SLF001
    # Codecov percent
    expected_percent = 85
    assert r._codecov_percent('dev') == expected_percent  # noqa: SLF001
    # CodeFactor grade
    assert r._codefactor_grade('main') == 'A'  # noqa: SLF001
