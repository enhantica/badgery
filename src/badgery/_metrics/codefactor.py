# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""CodeFactor grade metric."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from badgery.metrics import BaseMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


class CodeFactorMetric(BaseMetric):
    """CodeFactor letter grade per branch (env fallback)."""

    key = 'codefactor'
    label = 'Code quality from CodeFactor.io'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize CodeFactor metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_all(self, _args: object) -> None:
        """Read CodeFactor grades from environment variables."""
        self.master = os.environ.get('CI_CODEFACTOR_MASTER', '')
        self.develop = os.environ.get('CI_CODEFACTOR_DEVELOP', '')
        self.feature_value = os.environ.get('CI_CODEFACTOR_FEATURE', '')

    def badge(self, value: object) -> str:
        """Return a badge string (unused)."""
        return self.badge_gen.codefactor_badge(value)

    def refs(self) -> dict[str, str]:
        """Return CodeFactor overview URLs for branches."""
        cf = self.badge_gen.codefactor
        return {
            'master': self.badge('master'),
            'master_url': f'{cf}/overview',
            'develop': self.badge('develop'),
            'develop_url': f'{cf}/overview/develop',
            'feature': self.badge(self.feature),
            'feature_url': f'{cf}/overview/{self.feature}',
        }
