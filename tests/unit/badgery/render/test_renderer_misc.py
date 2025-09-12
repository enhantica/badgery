from __future__ import annotations

from badgery.badges import BadgeGenerator
from badgery.metrics import BaseMetric
from badgery.render import HTMLDashboardRenderer


def test_value_item_html_unknown_metric():
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('r/x'))
    html = r._value_item_html('nope', 'master', 'main')
    assert 'main: unknown' in html
    assert 'class="gray"' in html


def test_base_renderer_render_returns_empty_string():
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert r.render() == ''


def test_status_text_unknown_metric_type_and_ratio_gray():
    # Unknown metric type falls back to ('unknown', 'gray')
    class UnknownMetric(BaseMetric):
        key = 'u'

        def read_value(self, path: str):  # pragma: no cover - not used
            raise NotImplementedError

        def read_all(self, args):  # pragma: no cover - not used
            raise NotImplementedError

        def badge(self, value):  # pragma: no cover - not used
            return ''

    m = UnknownMetric(BadgeGenerator('r/x'), feature='f')
    r = HTMLDashboardRenderer([m], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert r._status_text_for_metric('u', 'master') == ('unknown', 'gray')

    # LinesOfCodeMetric ratio is gray when lloc is invalid or zero
    from badgery.metrics import LinesOfCodeMetric

    loc = LinesOfCodeMetric(BadgeGenerator('r/x'), feature='f')
    loc.master = (100, 0)
    r = HTMLDashboardRenderer([loc], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert r._status_text_for_metric('loc', 'master') == ('100/0', 'gray')

    loc2 = LinesOfCodeMetric(BadgeGenerator('r/x'), feature='f')
    loc2.master = (100, 'oops')  # invalid lloc triggers except path
    r2 = HTMLDashboardRenderer([loc2], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert r2._status_text_for_metric('loc', 'master') == ('100/-', 'gray')
