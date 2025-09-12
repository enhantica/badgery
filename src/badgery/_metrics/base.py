# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Base types and helpers for metrics."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import Never

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


def _detect_feature_branch() -> str:
    """Detect the feature branch name from common CI env vars.

    Returns:
        str: The detected branch name, or ``'unknown'`` if not present.
    """
    return (
        os.environ.get('CI_BRANCH')
        or os.environ.get('GITHUB_REF_NAME')
        or os.environ.get('GITHUB_HEAD_REF')
        or 'unknown'
    )


class BaseMetric:
    """Base abstraction for a metric rendered on three branches.

    Subclasses should implement `read_value` and `read_all`. They may
    override `format_value` and `badge` to customize display.
    """

    key: str = ''
    label: str = ''
    thresholds: ClassVar[list] = []
    reverse: bool = False
    badge_url_func: Any = None

    def __init__(
        self,
        badge_gen: BadgeGenerator,
        key: str | None = None,
        label: str | None = None,
        feature: str | None = None,
    ) -> None:
        """Initialize a metric and its runtime state."""
        self.badge_gen = badge_gen
        if key is not None:
            self.key = key
        if label is not None:
            self.label = label
        self.feature = feature or _detect_feature_branch()
        self.master = None
        self.develop = None
        self.feature_value = None

    @staticmethod
    def read_value(path: str) -> Never:
        """Read a single branch value from a file path."""
        raise NotImplementedError

    def read_all(self, args: object) -> Never:
        """Populate values for default, develop, and feature."""
        raise NotImplementedError

    @staticmethod
    def format_value(value: object) -> str:
        """Return a human-readable representation for `value`."""
        return str(value)

    def badge(self, value: object) -> Never:
        """Return a badge string for `value` (unused in HTML)."""
        raise NotImplementedError

    def refs(self) -> dict[str, str]:
        """Return a mapping of rendered badges per branch."""
        return {
            'master': self.badge(self.master),
            'master_url': '#',
            'develop': self.badge(self.develop),
            'develop_url': '#',
            'feature': self.badge(self.feature_value),
            'feature_url': '#',
        }
