# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Metric readers and adapters used by the dashboard renderer."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
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
            tuple[float | None, int | None]: Average MI and file
            count, or (None, None) if unavailable.
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
        self.master = self.read_value(args.maintainability_index_master)
        self.develop = self.read_value(args.maintainability_index_develop)
        self.feature_value = self.read_value(args.maintainability_index_feature)

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
        """Read average MI and file count.

        Returns:
            tuple[float | None, int | None]: Average MI and file
            count, or (None, None) if unavailable.
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
        self.master = self.read_value(args.cyclomatic_complexity_master)
        self.develop = self.read_value(args.cyclomatic_complexity_develop)
        self.feature_value = self.read_value(args.cyclomatic_complexity_feature)

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
            str: Percentage like "85%", or empty string if unknown.
        """
        if path and Path(path).exists():
            lines = Path(path).read_text(encoding='utf-8').splitlines()
            for line in lines:
                if line.startswith('| TOTAL'):
                    parts = line.split('|')
                    min_parts = 3
                    if len(parts) >= min_parts:
                        return parts[-2].strip()
            for line in reversed(lines):
                if 'actual:' in line:
                    after_actual = line.split('actual:')[-1].strip()
                    return after_actual.split()[0]
        return ''

    def read_all(self, args: object) -> None:
        """Populate coverage values for three branches."""
        self.master = self.read_value(args.coverage_docstring_master)
        self.develop = self.read_value(args.coverage_docstring_develop)
        self.feature_value = self.read_value(args.coverage_docstring_feature)

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


class GithubWorkflowMetric(BaseMetric):
    """Display GitHub Actions workflow status per branch."""

    def __init__(
        self,
        badge_gen: BadgeGenerator,
        workflow_filename: str,
        label: str,
        feature: str | None = None,
    ) -> None:
        """Initialize workflow metric with file name and label."""
        base = Path(workflow_filename).stem.replace('.', '-').replace('_', '-')
        key = base
        super().__init__(badge_gen, key=key, label=label, feature=feature)
        self.workflow_filename = workflow_filename

    @staticmethod
    def _env_key(base: str, branch: str) -> str:
        """Return the env var key for a workflow status.

        Args:
            base: Normalized workflow name (stem), e.g. ``ci``.
            branch: Branch label (``master``/``develop``/``feature``).

        Returns:
            str: The environment variable name to check.
        """
        return f'CI_WORKFLOW_{base.upper().replace("-", "_")}_{branch.upper()}'

    def read_all(self, _args: object) -> None:
        """Populate workflow status env vars for three branches."""
        base = self.key
        self.master = os.environ.get(self._env_key(base, 'master'), '')
        self.develop = os.environ.get(self._env_key(base, 'develop'), '')
        self.feature_value = os.environ.get(self._env_key(base, 'feature'), '')

    def badge(self, value: object) -> str:
        """Return a badge string (unused)."""
        return self.badge_gen.github_badge(self.workflow_filename, value)

    def refs(self) -> dict[str, str]:
        """Return workflow badge URLs for branches."""
        return {
            'master': self.badge('master'),
            'master_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
            'develop': self.badge('develop'),
            'develop_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
            'feature': self.badge(self.feature),
            'feature_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
        }


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


class LinesOfCodeMetric(BaseMetric):
    """Aggregate SLOC and LLOC from Radon raw metrics report."""

    key = 'loc'
    label = 'Source/Logical lines of code'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize line count metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _extract_sloc_lloc(obj: object) -> tuple[int, int]:
        """Recursively extract SLOC/LLOC from a JSON-like object.

        Returns:
            tuple[int, int]: The cumulative ``(sloc, lloc)`` pair.
        """
        sloc = 0
        lloc = 0
        if isinstance(obj, dict):
            if 'sloc' in obj or 'lloc' in obj:
                try:
                    sloc += int(obj.get('sloc', 0))
                    lloc += int(obj.get('lloc', 0))
                except Exception as exc:
                    logging.debug('raw-metrics sloc/lloc parse error: %s', exc)
            raw = obj.get('raw') if isinstance(obj.get('raw'), dict) else None
            if raw:
                try:
                    sloc += int(raw.get('sloc', 0))
                    lloc += int(raw.get('lloc', 0))
                except Exception as exc:
                    logging.debug('raw-metrics raw.sloc/lloc parse error: %s', exc)
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    s, lloc_part = LinesOfCodeMetric._extract_sloc_lloc(v)
                    sloc += s
                    lloc += lloc_part
        elif isinstance(obj, list):
            for it in obj:
                s, lloc_part = LinesOfCodeMetric._extract_sloc_lloc(it)
                sloc += s
                lloc += lloc_part
        return (sloc, lloc)

    @staticmethod
    def _sum_raw_metrics(path: str | None) -> tuple[int, int] | None:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        return LinesOfCodeMetric._extract_sloc_lloc(data)

    def read_all(self, args: object) -> None:
        """Populate SLOC/LLOC tuples for three branches."""
        self.master = self._sum_raw_metrics(getattr(args, 'raw_metrics_master', None))
        self.develop = self._sum_raw_metrics(getattr(args, 'raw_metrics_develop', None))
        self.feature_value = self._sum_raw_metrics(getattr(args, 'raw_metrics_feature', None))


class FileCountMetric(BaseMetric):
    """Count files from the Radon complexity JSON report."""

    key = 'files'
    label = 'Number of files'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize metric with badge generator and feature branch."""
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
        """Populate values for three branches."""
        self.master = self._count_files(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._count_files(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._count_files(
            getattr(args, 'cyclomatic_complexity_feature', None),
        )


class FunctionCountMetric(BaseMetric):
    """Count functions from the Radon complexity JSON report."""

    key = 'funcs'
    label = 'Number of functions'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize metric with badge generator and feature branch."""
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
        """Populate values for three branches."""
        self.master = self._count_functions(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._count_functions(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._count_functions(
            getattr(args, 'cyclomatic_complexity_feature', None),
        )
