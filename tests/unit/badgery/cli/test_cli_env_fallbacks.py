from __future__ import annotations

import sys
from pathlib import Path

import pytest

from badgery.cli import parse_args


def test_parse_args_env_fallbacks_used_when_reports_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Config points to non-existent files; args should fall back to env vars
    yml = tmp_path / '.badgery.yaml'
    yml.write_text(
        (
            'default_branch: main\n'
            'develop_branch: develop\n'
            'cards:\n'
            '  - group: Code Quality\n'
            '    type: radon_cc\n'
            '    report: missing/{branch}/cc.json\n'
            '  - group: Code Quality\n'
            '    type: radon_mi\n'
            '    report: missing/{branch}/mi.json\n'
            '  - group: Size\n'
            '    type: radon_loc\n'
            '    report: missing/{branch}/raw.json\n'
            '  - group: Coverage\n'
            '    type: interrogate\n'
            '    report: missing/{branch}/interrogate.txt\n'
        ),
        encoding='utf-8',
    )

    # Provide environment fallbacks
    monkeypatch.setenv('CI_COMPLEXITY_MASTER', '/env/cc-main.json')
    monkeypatch.setenv('CI_COMPLEXITY_DEVELOP', '/env/cc-develop.json')
    monkeypatch.setenv('CI_COMPLEXITY_FEATURE', '/env/cc-feature.json')
    monkeypatch.setenv('CI_MAINTAINABILITY_MASTER', '/env/mi-main.json')
    monkeypatch.setenv('CI_MAINTAINABILITY_DEVELOP', '/env/mi-develop.json')
    monkeypatch.setenv('CI_MAINTAINABILITY_FEATURE', '/env/mi-feature.json')
    monkeypatch.setenv('CI_RAW_METRICS_MASTER', '/env/raw-main.json')
    monkeypatch.setenv('CI_RAW_METRICS_DEVELOP', '/env/raw-develop.json')
    monkeypatch.setenv('CI_RAW_METRICS_FEATURE', '/env/raw-feature.json')
    monkeypatch.setenv('CI_DOCSTRING_MASTER', '/env/ds-main.txt')
    monkeypatch.setenv('CI_DOCSTRING_DEVELOP', '/env/ds-develop.txt')
    monkeypatch.setenv('CI_DOCSTRING_FEATURE', '/env/ds-feature.txt')

    argv = [
        'badgery',
        '--repo',
        'org/repo',
        '--branch',
        'feature-x',
        '--config',
        str(yml),
    ]
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.chdir(tmp_path)

    args = parse_args()
    # All should reflect env values because files do not exist
    assert args.cyclomatic_complexity_master == '/env/cc-main.json'
    assert args.cyclomatic_complexity_develop == '/env/cc-develop.json'
    assert args.cyclomatic_complexity_feature == '/env/cc-feature.json'
    assert args.maintainability_index_master == '/env/mi-main.json'
    assert args.maintainability_index_develop == '/env/mi-develop.json'
    assert args.maintainability_index_feature == '/env/mi-feature.json'
    assert args.raw_metrics_master == '/env/raw-main.json'
    assert args.raw_metrics_develop == '/env/raw-develop.json'
    assert args.raw_metrics_feature == '/env/raw-feature.json'
    assert args.coverage_docstring_master == '/env/ds-main.txt'
    assert args.coverage_docstring_develop == '/env/ds-develop.txt'
    assert args.coverage_docstring_feature == '/env/ds-feature.txt'

