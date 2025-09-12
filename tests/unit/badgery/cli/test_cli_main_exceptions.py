from __future__ import annotations

from pathlib import Path
from typing import Never

import pytest

from badgery import cli as cli_mod


class _Args:
    def __init__(self, output: Path) -> None:
        self.output = str(output)
        self.repo = 'org/repo'
        self.branch = 'f'
        self.cards_config = []
        self.default_branch = 'main'
        self.develop_branch = 'develop'
        self.log_level = 'ERROR'


def test_cli_main_handles_metric_read_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: parse_args returns our args
    args = _Args(tmp_path / 'out.html')
    monkeypatch.setattr(cli_mod, 'parse_args', lambda: args)

    # A fake metric that raises in read_all
    class RaisingMetric:
        key = 'raising'

        def read_all(self, _: object) -> Never:
            _ = self
            raise RuntimeError('boom')

    # build_metrics_from_config returns the raising metric and a simple spec
    monkeypatch.setattr(
        cli_mod,
        'build_metrics_from_config',
        lambda _cards, _bg, _f: ([RaisingMetric()], [('raising', 'R', 'i')]),
    )

    # Render returns deterministic output
    monkeypatch.setattr(cli_mod.HTMLDashboardRendererWithSpec, 'render', lambda _self: 'HTML')

    # Act: call main() and ensure it completes and writes the file
    cli_mod.main()
    assert Path(args.output).exists()
    assert Path(args.output).read_text(encoding='utf-8') == 'HTML'
