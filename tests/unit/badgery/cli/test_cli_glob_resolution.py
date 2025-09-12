from __future__ import annotations

import sys
from pathlib import Path

import pytest

from badgery.cli import parse_args


def test_parse_args_uses_glob_for_first_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Prepare reports with wildcard pattern in config
    reports = tmp_path / 'reports' / 'main'
    reports.mkdir(parents=True)
    (reports / 'cc-1.json').write_text('{"a.py": [{"complexity": 1}]}', encoding='utf-8')
    (reports / 'cc-2.json').write_text('{"a.py": [{"complexity": 2}]}', encoding='utf-8')

    yml = tmp_path / '.badgery.yaml'
    yml.write_text(
        (
            'default_branch: main\n'
            'develop_branch: develop\n'
            'cards:\n'
            '  - group: Code Quality\n'
            '    type: radon_cc\n'
            '    report: reports/{branch}/cc-*.json\n'
        ),
        encoding='utf-8',
    )

    argv = ['badgery', '--repo', 'org/repo', '--branch', 'feat', '--config', str(yml)]
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.chdir(tmp_path)

    args = parse_args()
    # Glob should return the first match; we accept any valid match among the two created
    assert Path(args.cyclomatic_complexity_master).parent.resolve() == reports.resolve()
    assert Path(args.cyclomatic_complexity_master).name in {'cc-1.json', 'cc-2.json'}
