from __future__ import annotations

import re
from typing import Never

from badgery.badges import BadgeGenerator
from badgery.metrics import BaseMetric
from badgery.metrics import LinesOfCodeMetric
from badgery.render import HTMLDashboardRenderer


def test_value_item_html_unknown_metric() -> None:
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('r/x'))
    html = r._value_item_html('nope', 'master', 'main')  # noqa: SLF001

    assert re.search(
        r'<span class="item-label(?: [^"]+)?">(?:\s*<i[^>]*></i>\s*)?main</span>',
        html,
    )
    assert 'item-value gray">unknown' in html


def test_base_renderer_render_returns_empty_string() -> None:
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert not r.render()


def test_status_text_unknown_metric_type_and_ratio_gray() -> None:
    # Unknown metric type falls back to ('unknown', 'gray')
    class UnknownMetric(BaseMetric):
        key = 'u'

        def read_value(self, path: str) -> Never:  # pragma: no cover - not used
            raise NotImplementedError

        def read_all(self, args: object) -> Never:  # pragma: no cover - not used
            raise NotImplementedError

        def badge(self, _value: object) -> str:  # pragma: no cover - not used
            _ = self
            return ''

    m = UnknownMetric(BadgeGenerator('r/x'), feature='f')
    r = HTMLDashboardRenderer([m], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert r._status_text_for_metric('u', 'master') == ('unknown', 'gray')  # noqa: SLF001

    # LinesOfCodeMetric ratio is gray when lloc is invalid or zero
    loc = LinesOfCodeMetric(BadgeGenerator('r/x'), feature='f')
    loc.master = (100, 0)
    r = HTMLDashboardRenderer([loc], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert r._status_text_for_metric('loc', 'master') == ('100/0', 'gray')  # noqa: SLF001

    loc2 = LinesOfCodeMetric(BadgeGenerator('r/x'), feature='f')
    loc2.master = (100, 'oops')  # invalid lloc triggers except path
    r2 = HTMLDashboardRenderer([loc2], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert r2._status_text_for_metric('loc', 'master') == ('100/-', 'gray')  # noqa: SLF001
