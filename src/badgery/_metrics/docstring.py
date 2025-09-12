# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Docstring coverage metric (Interrogate text report)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from badgery.metrics import BaseMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


PARTS_MIN = 3


class DocstringCoverageMetric(BaseMetric):
    """Docstring coverage percent from interrogate report."""

    key = 'docstring'
    label = 'Docstring coverage with interrogate'
    thresholds: ClassVar[list] = [
        (90, '', 'brightgreen'),
        (70, '', 'yellow'),
        (50, '', 'orange'),
        (0, '', 'red'),
    ]
    reverse = False

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize docstring coverage metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def read_value(path: str) -> str:
        """Read coverage percent string from text report file.

        Returns:
            str: Percentage string like ``"85%"``, or an empty string
            if not available.
        """
        if path and Path(path).exists():
            lines = Path(path).read_text(encoding='utf-8').splitlines()
            for line in lines:
                if line.startswith('| TOTAL'):
                    parts = line.split('|')
                    if len(parts) >= PARTS_MIN:
                        return parts[-2].strip()
            for line in reversed(lines):
                if 'actual:' in line:
                    after_actual = line.split('actual:')[-1].strip()
                    return after_actual.split()[0]
        return ''

    def read_all(self, args: object) -> None:
        """Populate coverage values for three branches."""
        self.master = self.read_value(getattr(args, 'coverage_docstring_master', None))
        self.develop = self.read_value(getattr(args, 'coverage_docstring_develop', None))
        self.feature_value = self.read_value(getattr(args, 'coverage_docstring_feature', None))

    @staticmethod
    def format_value(value: object) -> str:
        """Return a percentage string, defaulting to 0%."""
        if not value:
            return '0%'
        return value

    @staticmethod
    def badge(_value: object) -> str:
        """Return a badge string (unused)."""
        return ''
