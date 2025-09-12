from __future__ import annotations

from badgery.badges import BadgeGenerator
from badgery.config import build_metrics_from_config


def test_build_metrics_supports_codecove_alias():
    cards = [{'group': 'Coverage', 'type': 'codecove', 'title': 'Codecov'}]
    m, spec = build_metrics_from_config(cards, BadgeGenerator('org/repo'), feature='f')
    keys = {x.key for x in m}
    assert 'codecov' in keys
    assert any(s[0] == 'codecov' for s in spec)
