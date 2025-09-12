# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Maintainability Index metric (Radon JSON)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

from badgery.metrics import BaseMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


class MaintainabilityMetric(BaseMetric):
    """Average maintainability index and file count per branch."""

    key = 'maintainability'
    label = 'Maintainability index with radon'
    thresholds: ClassVar[list] = [
        (85, 'A', 'brightgreen'),
        (70, 'B', 'green'),
        (50, 'C', 'yellow'),
        (30, 'D', 'orange'),
        (0, 'F', 'red'),
    ]
    reverse = False

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize maintainability metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def read_value(path: str) -> tuple[float | None, int | None]:
        """Read average MI and file count.

        Returns:
            tuple[float | None, int | None]: Average maintainability
            index and number of files, or ``(None, None)`` if
            unavailable.
        """
        if path and Path(path).exists():
            try:
                data = json.loads(Path(path).read_text(encoding='utf-8'))
                mi_values = []
                for value in data.values():
                    if isinstance(value, dict):
                        mi = value.get('mi')
                        if isinstance(mi, (int, float)):
                            mi_values.append(mi)
                if mi_values:
                    avg_mi = sum(mi_values) / len(mi_values)
                    return (avg_mi, len(mi_values))
            except Exception as exc:
                logging.debug('Failed to read maintainability from %s: %s', path, exc)
        return (None, None)

    def read_all(self, args: object) -> None:
        """Populate MI values for default, develop, and feature."""
        self.master = self.read_value(getattr(args, 'maintainability_index_master', None))
        self.develop = self.read_value(getattr(args, 'maintainability_index_develop', None))
        self.feature_value = self.read_value(getattr(args, 'maintainability_index_feature', None))

    @staticmethod
    def format_value(value: object) -> str:
        """Return a human-readable MI summary for display."""
        if (
            not value
            or not isinstance(value, tuple)
            or value[0] is None
            or value[1] is None
            or value[1] == 0
        ):
            return 'unknown'
        mi, count = value
        mi_rounded = round(mi)
        return f'{mi_rounded} over {count} files'

    @staticmethod
    def badge(_value: object) -> str:
        """Return a badge string (unused in the HTML renderer)."""
        return ''
