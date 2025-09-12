from __future__ import annotations

import sys
from pathlib import Path

import pytest

from badgery.cli import parse_args


def _write_yaml(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def test_parse_args_resolves_report_paths_with_branch_placeholders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    # Prepare temp repo layout with reports per branch
    repo_root = tmp_path
    reports = repo_root / 'reports'
    for br in ('main', 'develop', 'feature-x'):
        d = reports / br
        d.mkdir(parents=True)
        # create expected report files
        (d / 'cc.json').write_text('{"a.py": [{"complexity": 2}]}', encoding='utf-8')
        (d / 'mi.json').write_text('{"a.py": {"mi": 80}}', encoding='utf-8')
        (d / 'raw.json').write_text('[{"sloc": 1, "lloc": 1}]', encoding='utf-8')
        (d / 'interrogate.txt').write_text('| TOTAL | X | 90% |', encoding='utf-8')

    # Project config with placeholders
    yml = repo_root / '.badgery.yaml'
    _write_yaml(
        yml,
        (
            'default_branch: main\n'
            'develop_branch: develop\n'
            '\n'
            'cards:\n'
            '  - group: Code Quality\n'
            '    type: radon_cc\n'
            '    title: CC\n'
            '    report: reports/{branch}/cc.json\n'
            '    enabled: true\n'
            '  - group: Code Quality\n'
            '    type: radon_mi\n'
            '    title: MI\n'
            '    report: reports/{branch}/mi.json\n'
            '    enabled: true\n'
            '  - group: Size\n'
            '    type: radon_loc\n'
            '    title: LOC\n'
            '    report: reports/{branch}/raw.json\n'
            '    enabled: true\n'
            '  - group: Coverage\n'
            '    type: interrogate\n'
            '    title: Docstrings\n'
            '    report: reports/{branch}/interrogate.txt\n'
            '    enabled: true\n'
        ),
    )

    # Run CLI arg parsing against the temp config
    monkeypatch.setenv('BADGES_LOG_LEVEL', 'ERROR')
    monkeypatch.setenv('PYTHONPATH', str((repo_root / 'src').resolve()))
    argv = [
        'badgery',
        '--repo',
        'org/repo',
        '--branch',
        'feature-x',
        '--config',
        str(yml),
        '--output',
        str(repo_root / 'BADGES.html'),
    ]
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1')
    monkeypatch.setenv('PYTHONWARNINGS', 'ignore')
    monkeypatch.setenv('LC_ALL', 'C')
    monkeypatch.setenv('LANG', 'C')
    monkeypatch.setattr(sys, 'argv', argv)

    # Ensure relative patterns resolve from the project root
    monkeypatch.chdir(repo_root)
    args = parse_args()

    # Complexity report paths
    assert (
        Path(args.cyclomatic_complexity_master).resolve()
        == (reports / 'main' / 'cc.json').resolve()
    )
    assert (
        Path(args.cyclomatic_complexity_develop).resolve()
        == (reports / 'develop' / 'cc.json').resolve()
    )
    assert (
        Path(args.cyclomatic_complexity_feature).resolve()
        == (reports / 'feature-x' / 'cc.json').resolve()
    )

    # MI report paths
    assert (
        Path(args.maintainability_index_master).resolve()
        == (reports / 'main' / 'mi.json').resolve()
    )
    assert (
        Path(args.maintainability_index_develop).resolve()
        == (reports / 'develop' / 'mi.json').resolve()
    )
    assert (
        Path(args.maintainability_index_feature).resolve()
        == (reports / 'feature-x' / 'mi.json').resolve()
    )

    # Raw metrics paths
    assert Path(args.raw_metrics_master).resolve() == (reports / 'main' / 'raw.json').resolve()
    assert Path(args.raw_metrics_develop).resolve() == (reports / 'develop' / 'raw.json').resolve()
    assert (
        Path(args.raw_metrics_feature).resolve() == (reports / 'feature-x' / 'raw.json').resolve()
    )

    # Docstring coverage paths
    assert (
        Path(args.coverage_docstring_master).resolve()
        == (reports / 'main' / 'interrogate.txt').resolve()
    )
    assert (
        Path(args.coverage_docstring_develop).resolve()
        == (reports / 'develop' / 'interrogate.txt').resolve()
    )
    assert (
        Path(args.coverage_docstring_feature).resolve()
        == (reports / 'feature-x' / 'interrogate.txt').resolve()
    )


def test_parse_args_dir_pattern_with_double_star(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Only test radon_cc resolution using "dir" with ** placeholder
    repo_root = tmp_path
    reports = repo_root / 'reports'
    for br in ('main', 'develop', 'feature-x'):
        d = reports / br
        d.mkdir(parents=True)
        (d / 'cc.json').write_text('{"a.py": []}', encoding='utf-8')

    yml = repo_root / '.badgery.yaml'
    _write_yaml(
        yml,
        (
            'default_branch: main\n'
            'develop_branch: develop\n'
            '\n'
            'cards:\n'
            '  - group: Code Quality\n'
            '    type: radon_cc\n'
            '    title: CC\n'
            '    dir: reports/**/cc.json\n'
            '    enabled: true\n'
        ),
    )

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

    # Ensure relative patterns resolve from the project root
    monkeypatch.chdir(repo_root)
    args = parse_args()

    # The code replaces "**" with branch name verbatim
    assert (
        Path(args.cyclomatic_complexity_master).resolve()
        == (reports / 'main' / 'cc.json').resolve()
    )
    assert (
        Path(args.cyclomatic_complexity_develop).resolve()
        == (reports / 'develop' / 'cc.json').resolve()
    )
    assert (
        Path(args.cyclomatic_complexity_feature).resolve()
        == (reports / 'feature-x' / 'cc.json').resolve()
    )
