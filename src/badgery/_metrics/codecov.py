# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Codecov coverage metric (env fallback)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from badgery.metrics import BaseMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


class CodecovMetric(BaseMetric):
    """Codecov unit test coverage percent per branch (from env)."""

    key = 'codecov'
    label = 'Unit test coverage from Codecov.io'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize Codecov coverage metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_all(self, _args: object) -> None:
        """Read coverage values from environment variables."""
        self.master = os.environ.get('CI_CODECOV_MASTER', '')
        self.develop = os.environ.get('CI_CODECOV_DEVELOP', '')
        self.feature_value = os.environ.get('CI_CODECOV_FEATURE', '')
