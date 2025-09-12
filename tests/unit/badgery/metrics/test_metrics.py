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
from badgery.metrics import GithubWorkflowMetric
from badgery.metrics import LinesOfCodeMetric
from badgery.metrics import MaintainabilityMetric


def test_maintainability_metric_reads_and_formats(tmp_path: Path):
    data = {'a.py': {'mi': 90}, 'b.py': {'mi': 70}}
    p = tmp_path / 'mi.json'
    p.write_text(json.dumps(data), encoding='utf-8')
    m = MaintainabilityMetric(BadgeGenerator('x/y'), feature='f')
    avg, count = m.read_value(str(p))
    expected_avg = 80.0
    expected_count = 2
    assert round(avg, 2) == expected_avg  # desired
    assert count == expected_count  # desired
    # formatted
    assert m.format_value((avg, count)) == '80 over 2 files'  # actual


def test_complexity_metric_reads_and_formats(tmp_path: Path):
    data = {'a.py': [{'complexity': 2}, {'complexity': 4}], 'b.py': []}
    p = tmp_path / 'cc.json'
    p.write_text(json.dumps(data), encoding='utf-8')
    m = ComplexityMetric(BadgeGenerator('x/y'), feature='f')
    avg, count = m.read_value(str(p))
    expected_avg3 = 3.0
    expected_two = 2
    assert round(avg, 3) == expected_avg3
    assert count == expected_two
    assert m.format_value((avg, count)) == '3.0 over 2 funcs'


def test_docstring_coverage_metric_reads_total_and_fallback(tmp_path: Path):
    # Case 1: table TOTAL line
    p1 = tmp_path / 'interrogate1.txt'
    p1.write_text('| TOTAL | something | 88% |', encoding='utf-8')
    m = DocstringCoverageMetric(BadgeGenerator('x/y'), feature='f')
    assert m.read_value(str(p1)) == '88%'

    # Case 2: fallback to "actual:" suffix
    p2 = tmp_path / 'interrogate2.txt'
    p2.write_text('overall blah actual: 77% of items', encoding='utf-8')
    assert m.read_value(str(p2)) == '77%'

    # Case 3: unknown
    assert not m.read_value(str(tmp_path / 'missing.txt'))


def test_lines_of_code_metric_sums_simple_list(tmp_path: Path):
    # Use list-based structure to avoid double-counting raw nested objects
    p = tmp_path / 'raw.json'
    p.write_text(json.dumps([{'sloc': 3, 'lloc': 2}, {'sloc': 7, 'lloc': 5}]), encoding='utf-8')
    m = LinesOfCodeMetric(BadgeGenerator('x/y'), feature='f')
    m.read_all(
        type(
            'Args',
            (),
            {
                'raw_metrics_master': str(p),
                'raw_metrics_develop': str(p),
                'raw_metrics_feature': str(p),
            },
        ),
    )
    assert m.master == (10, 7)
    assert m.develop == (10, 7)
    assert m.feature_value == (10, 7)


def test_file_and_function_count_metrics(tmp_path: Path):
    data = {
        'a.py': [{'complexity': 1}, {'complexity': 2}],
        'b.py': [],
        'c.py': 'not-a-list',
    }
    p = tmp_path / 'cc.json'
    p.write_text(json.dumps(data), encoding='utf-8')

    fc = FileCountMetric(BadgeGenerator('x/y'), feature='f')
    fc.read_all(
        type(
            'Args',
            (),
            {
                'cyclomatic_complexity_master': str(p),
                'cyclomatic_complexity_develop': str(p),
                'cyclomatic_complexity_feature': str(p),
            },
        ),
    )
    expected_files_total = 2
    assert fc.master == expected_files_total  # only keys with list values
    assert fc.develop == expected_files_total
    assert fc.feature_value == expected_files_total

    fnc = FunctionCountMetric(BadgeGenerator('x/y'), feature='f')
    fnc.read_all(
        type(
            'Args',
            (),
            {
                'cyclomatic_complexity_master': str(p),
                'cyclomatic_complexity_develop': str(p),
                'cyclomatic_complexity_feature': str(p),
            },
        ),
    )
    expected_funcs_total = 2
    assert fnc.master == expected_funcs_total
    assert fnc.develop == expected_funcs_total
    assert fnc.feature_value == expected_funcs_total


def test_codecov_and_codefactor_env_metrics(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('CI_CODECOV_MASTER', '82%')
    monkeypatch.setenv('CI_CODECOV_DEVELOP', '79%')
    monkeypatch.setenv('CI_CODECOV_FEATURE', '75%')
    cc = CodecovMetric(BadgeGenerator('r/x'), feature='f')
    cc.read_all(object())
    assert cc.master == '82%'
    assert cc.develop == '79%'
    assert cc.feature_value == '75%'

    monkeypatch.setenv('CI_CODEFACTOR_MASTER', 'A')
    monkeypatch.setenv('CI_CODEFACTOR_DEVELOP', 'B')
    monkeypatch.setenv('CI_CODEFACTOR_FEATURE', 'C')
    cf = CodeFactorMetric(BadgeGenerator('r/x'), feature='f')
    cf.read_all(object())
    assert cf.master == 'A'
    assert cf.develop == 'B'
    assert cf.feature_value == 'C'


def test_github_workflow_metric_refs_and_env(monkeypatch: pytest.MonkeyPatch):
    # Key base is derived from workflow stem: 'ci.yml' -> 'ci'
    monkeypatch.setenv('CI_WORKFLOW_CI_MASTER', 'passed')
    monkeypatch.setenv('CI_WORKFLOW_CI_DEVELOP', 'failed')
    monkeypatch.setenv('CI_WORKFLOW_CI_FEATURE', 'queued')
    bg = BadgeGenerator('acme/repo')
    gw = GithubWorkflowMetric(bg, workflow_filename='ci.yml', label='CI', feature='feature-x')
    gw.read_all(object())
    # Captured environment values
    assert gw.master == 'passed'
    assert gw.develop == 'failed'
    assert gw.feature_value == 'queued'
    # Badge image links derived from BadgeGenerator helpers
    assert bg.github_workflow_badge_img('ci.yml', None).endswith('/badge.svg')
    assert bg.github_workflow_badge_img('ci.yml', 'feature-x').endswith(
        '/badge.svg?branch=feature-x',
    )
