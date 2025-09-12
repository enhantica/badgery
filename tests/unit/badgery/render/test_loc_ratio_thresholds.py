from __future__ import annotations

from badgery.badges import BadgeGenerator
from badgery.metrics import LinesOfCodeMetric
from badgery.render import HTMLDashboardRenderer


def _status(loc_tuple):
    loc = LinesOfCodeMetric(BadgeGenerator('r/x'), feature='f')
    loc.master = loc_tuple
    r = HTMLDashboardRenderer([loc], feature='f', badge_gen=BadgeGenerator('r/x'))
    return r._status_text_for_metric('loc', 'master')


def test_loc_ratio_color_thresholds_orange_and_yellow():
    # Yellow when 1.25 >= ratio > 1.1
    assert _status((125, 100))[1] == 'yellow'
    # Orange when 1.5 >= ratio > 1.25
    assert _status((140, 100))[1] == 'orange'

