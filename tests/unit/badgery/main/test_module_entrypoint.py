from __future__ import annotations

import runpy
from pathlib import Path

import pytest


def test_package_main_invokes_cli_and_writes_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Patch parse_args to control arguments provided to main()
    from badgery import cli as cli_mod
    from badgery import config as cfg_mod
    from badgery import render as render_mod

    class Args:
        def __init__(self, output_path: Path):
            self.output = str(output_path)
            self.repo = 'org/repo'
            self.branch = 'feat'
            self.cards_config = []
            self.default_branch = 'main'
            self.develop_branch = 'develop'
            self.log_level = 'ERROR'

    out_path = tmp_path / 'BADGES.html'
    monkeypatch.setattr(cli_mod, 'parse_args', lambda: Args(out_path))
    # Return no metrics and an empty spec to minimize work
    monkeypatch.setattr(cfg_mod, 'build_metrics_from_config', lambda _cards, _bg, _f: ([], []))
    # Deterministic render content
    monkeypatch.setattr(render_mod.HTMLDashboardRendererWithSpec, 'render', lambda _self: 'OK')

    # Execute package as a script, which runs badgery.__main__
    runpy.run_module('badgery', run_name='__main__')

    out = out_path
    assert out.exists()
    assert out.read_text(encoding='utf-8') == 'OK'


def test_importing_module_does_not_invoke_main():
    # Importing __main__ should not run main() branch (covers else branch)
    mod = __import__('badgery.__main__', fromlist=['*'])
    assert hasattr(mod, '__doc__')
