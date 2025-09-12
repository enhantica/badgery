from __future__ import annotations

import sys
from pathlib import Path

import pytest

from badgery.cli import parse_args


def test_parse_args_skips_disabled_cards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reports = tmp_path / 'reports'
    (reports / 'feat').mkdir(parents=True)
    (reports / 'feat' / 'cc.json').write_text('{"a.py": []}', encoding='utf-8')

    yml = tmp_path / '.badgery.yaml'
    # First radon_cc is disabled and points to a non-existent path; second is enabled
    yml.write_text(
        (
            'default_branch: main\n'
            'develop_branch: develop\n'
            'cards:\n'
            '  - group: Code Quality\n'
            '    type: radon_cc\n'
            '    report: reports/bad/cc.json\n'
            '    enabled: false\n'
            '  - group: Code Quality\n'
            '    type: radon_cc\n'
            '    report: reports/{branch}/cc.json\n'
            '    enabled: true\n'
        ),
        encoding='utf-8',
    )

    argv = ['badgery', '--repo', 'org/repo', '--branch', 'feat', '--config', str(yml)]
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.chdir(tmp_path)

    args = parse_args()
    assert Path(args.cyclomatic_complexity_feature).resolve() == (reports / 'feat' / 'cc.json').resolve()

