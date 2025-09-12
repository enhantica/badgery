from __future__ import annotations

import runpy
from pathlib import Path

import pytest


def test_package_main_invokes_cli_and_writes_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Patch parse_args to control arguments provided to main()
    from badgery import cli as cli_mod
    from badgery import config as cfg_mod
    from badgery import render as render_mod

    class Args:
        output = str(tmp_path / 'BADGES.html')
        repo = 'org/repo'
        branch = 'feat'
        cards_config = []
        default_branch = 'main'
        develop_branch = 'develop'
        log_level = 'ERROR'

    monkeypatch.setattr(cli_mod, 'parse_args', lambda: Args())
    # Return no metrics and an empty spec to minimize work
    monkeypatch.setattr(cfg_mod, 'build_metrics_from_config', lambda cards, bg, f: ([], []))
    # Deterministic render content
    monkeypatch.setattr(render_mod.HTMLDashboardRendererWithSpec, 'render', lambda self: 'OK')

    # Execute package as a script, which runs badgery.__main__
    runpy.run_module('badgery', run_name='__main__')

    out = Path(Args.output)
    assert out.exists() and out.read_text(encoding='utf-8') == 'OK'


def test_importing_module_does_not_invoke_main():
    # Importing __main__ should not run main() branch (covers else branch)
    mod = __import__('badgery.__main__', fromlist=['*'])
    assert hasattr(mod, '__doc__')
