from __future__ import annotations

from badgery.badges import BadgeGenerator
from badgery.metrics import BaseMetric
from badgery.metrics import ComplexityMetric
from badgery.metrics import DocstringCoverageMetric
from badgery.metrics import FileCountMetric
from badgery.metrics import FunctionCountMetric
from badgery.metrics import LinesOfCodeMetric
from badgery.metrics import MaintainabilityMetric
from badgery.render import HTMLDashboardRendererWithSpec


def _set_values(m: BaseMetric, master, develop, feature):
    m.master = master
    m.develop = develop
    m.feature_value = feature


def test_html_render_end_to_end_smoke():
    # Create real metric instances but inject values directly
    bg = BadgeGenerator('org/repo')
    feature = 'feature-x'

    mi = MaintainabilityMetric(bg, feature=feature)
    _set_values(mi, (85.0, 10), (65.0, 10), (45.0, 10))  # grades A, B, C

    cc = ComplexityMetric(bg, feature=feature)
    _set_values(cc, (3.0, 20), (12.0, 20), (25.0, 20))  # grades A, C, D/F

    dc = DocstringCoverageMetric(bg, feature=feature)
    _set_values(dc, '92%', '76%', '60%')

    loc = LinesOfCodeMetric(bg, feature=feature)
    _set_values(loc, (90, 90), (110, 100), (200, 80))  # ratio 1.00, 1.10, 2.50

    files = FileCountMetric(bg, feature=feature)
    _set_values(files, 12, 11, 13)

    funcs = FunctionCountMetric(bg, feature=feature)
    _set_values(funcs, 120, 110, 130)

    metrics = [mi, cc, dc, loc, files, funcs]
    cards_spec = [
        (mi.key, 'Maintainability', 'fas fa-gauge'),
        (cc.key, 'Complexity', 'fas fa-gauge'),
        (dc.key, 'Docstrings', 'fas fa-square-poll-vertical'),
        (loc.key, 'LOC', 'fas fa-file-code'),
        (files.key, 'Files', 'fas fa-file-code'),
        (funcs.key, 'Functions', 'fas fa-file-code'),
    ]

    r = HTMLDashboardRendererWithSpec(
        metrics,
        feature,
        bg,
        cards_spec,
        default_branch='main',
        develop_branch='develop',
    )
    html = r.render()

    # Basic structure and labels
    assert '<div class="card-grid">' in html
    assert 'Maintainability' in html
    assert 'Complexity' in html
    assert 'Docstrings' in html

    # Status lines include branch labels and values
    assert 'main: A (85)' in html
    assert 'develop: B (65)' in html
    assert 'feature-x: C (45)' in html

    assert 'main: A (3.0)' in html
    assert 'develop: C (12.0)' in html
    assert 'feature-x: D (25.0)' in html or 'feature-x: F (25.0)' in html

    assert 'main: 92%' in html
    assert 'develop: 76%' in html
    assert 'feature-x: 60%' in html

    # LOC card includes ratio and tuple formatting
    assert 'main: 1.00 (90/90)' in html
    assert 'develop: 1.10 (110/100)' in html
    assert 'feature-x: 2.50 (200/80)' in html

    # Counts are formatted as blue text values (class color asserted indirectly via presence)
    assert 'Files' in html and 'main: 12' in html
    assert 'Functions' in html and 'develop: 110' in html
