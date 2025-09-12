# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Cyclomatic complexity metric (Radon JSON)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from badgery.metrics import BaseMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


class ComplexityMetric(BaseMetric):
    """Average cyclomatic complexity and item count per branch."""

    key = 'complexity'
    label = 'Cyclomatic complexity with radon'
    thresholds: ClassVar[list] = [
        (5, 'A', 'brightgreen'),
        (10, 'B', 'green'),
        (15, 'C', 'yellow'),
        (20, 'D', 'orange'),
    ]
    reverse = True

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize complexity metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def read_value(path: str) -> tuple[float | None, int | None]:
        """Read average complexity and item count.

        Returns:
            tuple[float | None, int | None]: Average cyclomatic
            complexity and number of analyzed items, or ``(None,
            None)`` if unavailable.
        """
        if not (path and Path(path).exists()):
            return (None, None)
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception as exc:
            logging.debug('Failed to read complexity from %s: %s', path, exc)
            return (None, None)
        if not isinstance(data, dict):
            return (None, None)
        values = [
            item.get('complexity')
            for file_data in data.values()
            if isinstance(file_data, list)
            for item in file_data
            if isinstance(item, dict) and isinstance(item.get('complexity'), (int, float))
        ]
        if values:
            avg_complexity = sum(values) / len(values)
            return (avg_complexity, len(values))
        return (None, None)

    def read_all(self, args: object) -> None:
        """Populate complexity values for three branches."""
        self.master = self.read_value(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self.read_value(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self.read_value(getattr(args, 'cyclomatic_complexity_feature', None))

    @staticmethod
    def format_value(value: object) -> str:
        """Return human-readable average complexity summary."""
        if (
            not value
            or not isinstance(value, tuple)
            or value[0] is None
            or value[1] is None
            or value[1] == 0
        ):
            return 'unknown'
        avg, count = value
        return f'{avg:.1f} over {count} funcs'

    @staticmethod
    def badge(_value: object) -> str:
        """Return a badge string (unused)."""
        return ''
