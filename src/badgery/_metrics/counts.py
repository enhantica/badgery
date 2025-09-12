# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""File and function count metrics (Radon complexity JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from badgery.metrics import BaseMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


class FileCountMetric(BaseMetric):
    """Count files from the Radon complexity JSON report."""

    key = 'files'
    label = 'Number of files'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize file count metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _count_files(path: str | None) -> int | None:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        if isinstance(data, dict):
            return len([k for k, v in data.items() if isinstance(v, list)])
        return None

    def read_all(self, args: object) -> None:
        """Populate file counts for default, develop, and feature."""
        self.master = self._count_files(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._count_files(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._count_files(
            getattr(args, 'cyclomatic_complexity_feature', None)
        )


class FunctionCountMetric(BaseMetric):
    """Count functions from the Radon complexity JSON report."""

    key = 'funcs'
    label = 'Number of functions'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize function count metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _count_functions(path: str | None) -> int | None:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        total = 0
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    total += len(v)
        return total if total else None

    def read_all(self, args: object) -> None:
        """Populate function counts for three branches."""
        self.master = self._count_functions(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._count_functions(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._count_functions(
            getattr(args, 'cyclomatic_complexity_feature', None)
        )


class FunctionsPerFileMetric(BaseMetric):
    """Compute functions-per-file ratio from Radon complexity JSON.

    Exposes tuple values per branch: ``(functions, files)`` so the
    renderer can compute and colorize the ratio and show both numbers
    in parentheses.
    """

    key = 'funcs_per_file'
    label = 'Functions/Files count (radon)'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize functions-per-file ratio metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _read_counts(path: str | None) -> tuple[int | None, int | None]:
        if not path or not Path(path).exists():
            return (None, None)
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return (None, None)
        files = 0
        funcs = 0
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    files += 1
                    funcs += len(v)
        if files == 0 and funcs == 0:
            return (None, None)
        return (funcs or None, files or None)

    def read_all(self, args: object) -> None:
        """Populate (functions, files) tuples for three branches."""
        self.master = self._read_counts(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._read_counts(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._read_counts(
            getattr(args, 'cyclomatic_complexity_feature', None)
        )
