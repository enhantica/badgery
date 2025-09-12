from __future__ import annotations

import re

from badgery.badges import BadgeGenerator
from badgery.metrics import BaseMetric
from badgery.metrics import ComplexityMetric
from badgery.metrics import DocstringCoverageMetric
from badgery.metrics import FileCountMetric
from badgery.metrics import FunctionCountMetric
from badgery.metrics import FunctionsPerFileMetric
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

    fpf = FunctionsPerFileMetric(bg, feature=feature)
    # functions-per-file takes (functions, files) tuples per branch
    _set_values(fpf, (120, 12), (110, 11), (130, 13))

    metrics = [mi, cc, dc, loc, fpf]
    cards_spec = [
        (mi.key, 'Maintainability', 'fas fa-gauge'),
        (cc.key, 'Complexity', 'fas fa-gauge'),
        (dc.key, 'Docstrings', 'fas fa-square-poll-vertical'),
        (loc.key, 'LOC', 'fas fa-file-code'),
        (fpf.key, 'Functions per file', 'fas fa-file-code'),
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

    # Status lines include branch labels and values (split into label/value spans)
    labels = re.findall(
        r'<span class="item-label(?: [^"]+)?">(?:\s*<i[^>]*></i>\s*)?([^<]+)</span>', html,
    )
    assert 'main' in labels
    assert 'develop' in labels
    assert 'feature-x' in labels
    assert 'A (85)' in html
    assert 'B (65)' in html
    assert 'C (45)' in html

    assert 'A (3.0)' in html
    assert 'C (12.0)' in html
    assert ('D (25.0)' in html) or ('F (25.0)' in html)

    assert '92%' in html
    assert '76%' in html
    assert '60%' in html

    # LOC card includes ratio and tuple formatting
    assert '1.00 (90/90)' in html
    assert '1.10 (110/100)' in html
    assert '2.50 (200/80)' in html

    # Functions per file card shows ratio and (funcs/files)
    assert 'Functions per file' in html
    assert '10.00 (120/12)' in html
    assert '10.00 (110/11)' in html
    assert '10.00 (130/13)' in html

    # Branch icons are present
    assert 'fas fa-crown' in html
    assert 'fas fa-hammer' in html
    assert 'fas fa-code-branch' in html
