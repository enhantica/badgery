from __future__ import annotations

from pathlib import Path

from badgery.badges import BadgeGenerator
from badgery.metrics import ComplexityMetric
from badgery.metrics import MaintainabilityMetric
from badgery.metrics import FileCountMetric
from badgery.metrics import FunctionCountMetric
from badgery.metrics import LinesOfCodeMetric
from badgery.metrics import MaintainabilityMetric


def test_metric_formatters_unknown_values(tmp_path: Path):
    bg = BadgeGenerator('r/x')
    mi = MaintainabilityMetric(bg, feature='f')
    assert mi.format_value((None, None)) == 'unknown'
    assert mi.format_value(None) == 'unknown'

    cc = ComplexityMetric(bg, feature='f')
    assert cc.format_value((None, None)) == 'unknown'
    assert cc.format_value(None) == 'unknown'


def test_lines_of_code_invalid_json_returns_none(tmp_path: Path):
    p = tmp_path / 'raw.json'
    p.write_text('not-json', encoding='utf-8')
    loc = LinesOfCodeMetric(BadgeGenerator('r/x'), feature='f')
    args = type('Args', (), {"raw_metrics_master": str(p), "raw_metrics_develop": str(p), "raw_metrics_feature": str(p)})
    loc.read_all(args)
    assert loc.master is None and loc.develop is None and loc.feature_value is None


def test_file_and_function_count_invalid_or_missing(tmp_path: Path):
    bad = tmp_path / 'bad.json'
    bad.write_text('oops', encoding='utf-8')
    fc = FileCountMetric(BadgeGenerator('r/x'), feature='f')
    fn = FunctionCountMetric(BadgeGenerator('r/x'), feature='f')
    args = type('Args', (), {"cyclomatic_complexity_master": str(bad), "cyclomatic_complexity_develop": str(bad), "cyclomatic_complexity_feature": str(bad)})
    fc.read_all(args)
    fn.read_all(args)
    assert fc.master is None and fn.master is None


def test_maintainability_and_complexity_read_value_invalid_json(tmp_path: Path):
    bad = tmp_path / 'bad.json'
    bad.write_text('oops', encoding='utf-8')
    mi = MaintainabilityMetric(BadgeGenerator('r/x'), feature='f')
    cc = ComplexityMetric(BadgeGenerator('r/x'), feature='f')
    assert mi.read_value(str(bad)) == (None, None)
    assert cc.read_value(str(bad)) == (None, None)
