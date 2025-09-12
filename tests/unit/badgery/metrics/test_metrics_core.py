from __future__ import annotations

import json
from pathlib import Path

import pytest

from badgery.badges import BadgeGenerator
from badgery.metrics import CodecovMetric
from badgery.metrics import CodeFactorMetric
from badgery.metrics import ComplexityMetric
from badgery.metrics import DocstringCoverageMetric
from badgery.metrics import FileCountMetric
from badgery.metrics import FunctionCountMetric
from badgery.metrics import LinesOfCodeMetric
from badgery.metrics import MaintainabilityMetric


def test_maintainability_read_value_and_format(tmp_path: Path):
    data = {'a.py': {'mi': 80}, 'b.py': {'mi': 50}, 'c.py': {'mi': 70}}
    p = tmp_path / 'mi.json'
    p.write_text(json.dumps(data), encoding='utf-8')
    m = MaintainabilityMetric(BadgeGenerator('r/x'))
    avg, count = m.read_value(str(p))
    assert round(avg) == 67
    assert count == 3
    # Human-readable format
    assert m.format_value((66.6, 3)).endswith('over 3 files')


def test_complexity_read_value(tmp_path: Path):
    data = {
        'a.py': [{'complexity': 3}, {'complexity': 8}],
        'b.py': [{'complexity': 10}],
    }
    p = tmp_path / 'cc.json'
    p.write_text(json.dumps(data), encoding='utf-8')
    c = ComplexityMetric(BadgeGenerator('r/x'))
    avg, count = c.read_value(str(p))
    assert pytest.approx(avg, rel=1e-6) == (3 + 8 + 10) / 3
    assert count == 3


def test_lines_of_code_sum_raw_metrics(tmp_path: Path):
    # Use flat keys to align with current aggregation behavior
    data = {
        'x': {'sloc': 10, 'lloc': 5},
        'y': {'sloc': 20, 'lloc': 10},
    }
    p = tmp_path / 'raw.json'
    p.write_text(json.dumps(data), encoding='utf-8')
    loc = LinesOfCodeMetric(BadgeGenerator('r/x'))
    sloc, lloc = loc._sum_raw_metrics(str(p))  # noqa: SLF001
    assert sloc == 30
    assert lloc == 15


def test_file_and_function_counts(tmp_path: Path):
    data = {
        'a.py': [{'n': 1}, {'n': 2}, {'n': 3}],
        'b.py': [{'n': 1}],
    }
    p = tmp_path / 'cc.json'
    p.write_text(json.dumps(data), encoding='utf-8')

    files = FileCountMetric(BadgeGenerator('r/x'))
    funcs = FunctionCountMetric(BadgeGenerator('r/x'))

    # Private helpers used via read_all; call directly for clarity
    assert files._count_files(str(p)) == 2  # noqa: SLF001
    assert funcs._count_functions(str(p)) == 4  # noqa: SLF001


def test_docstring_coverage_read_value_from_table_and_fallback(tmp_path: Path):
    t = tmp_path / 'doc.txt'
    t.write_text('header\n| TOTAL | 10 | 30% |', encoding='utf-8')
    d = DocstringCoverageMetric(BadgeGenerator('r/x'))
    assert d.read_value(str(t)) == '30%'

    # Fallback parse of "actual:" line
    t2 = tmp_path / 'doc2.txt'
    t2.write_text('something actual: 45% more', encoding='utf-8')
    assert d.read_value(str(t2)) == '45%'


def test_codecov_and_codefactor_read_all_from_env(monkeypatch):
    monkeypatch.setenv('CI_CODECOV_MASTER', '80%')
    monkeypatch.setenv('CI_CODECOV_DEVELOP', '82%')
    monkeypatch.setenv('CI_CODECOV_FEATURE', '70%')

    cov = CodecovMetric(BadgeGenerator('r/x'))
    cov.read_all(object())
    assert cov.master == '80%'
    assert cov.develop == '82%'
    assert cov.feature_value == '70%'

    monkeypatch.setenv('CI_CODEFACTOR_MASTER', 'A')
    monkeypatch.setenv('CI_CODEFACTOR_DEVELOP', 'B')
    monkeypatch.setenv('CI_CODEFACTOR_FEATURE', 'C')
    cf = CodeFactorMetric(BadgeGenerator('r/x'))
    cf.read_all(object())
    assert cf.master == 'A'
    assert cf.develop == 'B'
    assert cf.feature_value == 'C'
