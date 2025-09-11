"""Generate a dashboard-like HTML for the repository.

This tool renders a compact status board for several metrics and CI
workflows across three branches: ``master``, ``develop``, and the
current feature branch. It is a single-file utility that follows
clean structure and best practices (typing, docstrings, separation of
concerns, logging, and robust error handling).

Inputs are read from environment variables (to work well in CI) and
from a few CLI flags.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path
from glob import glob
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import urlopen

# Configuration

# GitHub repository, e.g. "easyscience/diffraction-lib"
REPO_DEFAULT = os.environ.get('GITHUB_REPOSITORY', 'easyscience/diffraction-lib')

# (no external badge providers)


def assign_grade(
    value: float,
    thresholds: list[tuple[float, str, str]],
    reverse: bool = False,
) -> tuple[str, str]:
    """Return a (grade, color) for a value.

    - thresholds: sequence of (threshold, grade, color) checked in order
    - reverse: match if value < threshold; else value >= threshold
    """
    for threshold, grade, color in thresholds:
        if reverse:
            if value < threshold:
                return grade, color
        else:
            if value >= threshold:
                return grade, color
    return '?', 'lightgrey'


# file: badges/generator.py
class BadgeGenerator:
    """Minimal link container and helpers for service URLs."""

    def __init__(self, repo: str = REPO_DEFAULT, shields: str = '') -> None:
        self.repo = repo
        self.shields = shields
        # Compute URLs based on repo
        # For github_workflows, use https://github.com/{repo}/actions/workflows
        self.github_workflows = f'https://github.com/{self.repo}/actions/workflows'
        # For codefactor, use https://www.codefactor.io/repository/github/{repo}
        self.codefactor = f'https://www.codefactor.io/repository/github/{self.repo}'
        # For codecov, use https://codecov.io/gh/{repo}
        self.codecov = f'https://codecov.io/gh/{self.repo}'

    def _badge(self, section: str, branch: str, extra_params: Dict[str, str] | None = None) -> str:
        return ''

    def codecov_badge(self, branch: str = 'master') -> str:
        return ''

    def codefactor_badge(self, branch: str = 'master') -> str:
        return ''

    def github_workflow_badge_img(self, workflow: str, branch: str | None = None) -> str:
        base = f'https://github.com/{self.repo}/actions/workflows/{workflow}/badge.svg'
        if branch and branch not in ('', 'master'):
            return f'{base}?branch={branch}'
        return base

    def github_workflow_badge_link(self, workflow: str) -> str:
        return f'https://github.com/{self.repo}/actions/workflows/{workflow}'

    def codecov_badge_img(self, branch: str | None = None) -> str:
        token = os.environ.get('CODECOV_TOKEN', 'qtsB5Q5BXO')
        repo = os.environ.get('CODECOV_REPO', self.repo)
        if branch and branch not in ('', 'master'):
            return f'https://codecov.io/gh/{repo}/branch/{branch}/graph/badge.svg?token={token}'
        return f'https://codecov.io/gh/{repo}/graph/badge.svg?token={token}'

    def codecov_badge_link(self) -> str:
        repo = os.environ.get('CODECOV_REPO', self.repo)
        return f'https://codecov.io/gh/{repo}'

    def codefactor_badge_img(self, branch: str) -> str:
        return f'https://www.codefactor.io/repository/github/{self.repo}/badge/{branch}'

    def codefactor_badge_link(self, branch: str) -> str:
        return f'https://www.codefactor.io/repository/github/{self.repo}/overview/{branch}'

    def docstring_badge(self, coverage: str) -> str:
        return ''

    def github_badge(self, workflow: str, branch: str = '') -> str:
        return ''

    def github_badge_set(self, workflow: str, feature_branch: str) -> Dict[str, str]:
        return {
            'master': '',
            'master_url': '#',
            'develop': '',
            'develop_url': '#',
            'feature': '',
            'feature_url': '#',
        }

    def complexity_badge(self, value: tuple) -> str:
        return ''

    def maintainability_badge(self, value) -> str:
        return ''


# --- Metrics Base and Subclasses ---


class BaseMetric:
    """Base abstraction for a metric that can render badges for
    branches.
    """

    key: str = ''
    label: str = ''
    thresholds: list = []
    reverse: bool = False
    badge_url_func: Any = None  # Can be function or method

    def __init__(self, badge_gen, key=None, label=None, feature=None):
        self.badge_gen = badge_gen
        if key is not None:
            self.key = key
        if label is not None:
            self.label = label
        # Feature: explicit if provided; else from env; else "unknown"
        self.feature = feature or _detect_feature_branch()
        self.master = None
        self.develop = None
        self.feature_value = None

    def read_value(self, path: str):
        """Override in subclass."""
        raise NotImplementedError

    def read_all(self, args):
        """Override in subclass to set .master, .develop,
        .feature_value.
        """
        raise NotImplementedError

    def format_value(self, value):
        """Override in subclass."""
        return str(value)

    def badge(self, value):
        """Override in subclass if needed, or call badge_gen method."""
        raise NotImplementedError

    def refs(self):
        return {
            'master': self.badge(self.master),
            'master_url': '#',
            'develop': self.badge(self.develop),
            'develop_url': '#',
            'feature': self.badge(self.feature_value),
            'feature_url': '#',
        }


class MaintainabilityMetric(BaseMetric):
    key = 'maintainability'
    label = 'Maintainability index with radon'
    thresholds = [
        (85, 'A', 'brightgreen'),
        (70, 'B', 'green'),
        (50, 'C', 'yellow'),
        (30, 'D', 'orange'),
        (0, 'F', 'red'),
    ]
    reverse = False

    def __init__(self, badge_gen, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_value(self, path: str):
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

    def read_all(self, args):
        self.master = self.read_value(args.maintainability_index_master)
        self.develop = self.read_value(args.maintainability_index_develop)
        self.feature_value = self.read_value(args.maintainability_index_feature)

    def format_value(self, value):
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

    def badge(self, value):
        return ''


class ComplexityMetric(BaseMetric):
    key = 'complexity'
    label = 'Cyclomatic complexity with radon'
    thresholds = [
        (5, 'A', 'brightgreen'),
        (10, 'B', 'green'),
        (15, 'C', 'yellow'),
        (20, 'D', 'orange'),
    ]
    reverse = True

    def __init__(self, badge_gen, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_value(self, path: str):
        if path and Path(path).exists():
            try:
                data = json.loads(Path(path).read_text(encoding='utf-8'))
                complexities = []
                for file_data in data.values():
                    if isinstance(file_data, list):
                        for item in file_data:
                            if isinstance(item, dict):
                                complexity_value = item.get('complexity')
                                if isinstance(complexity_value, (int, float)):
                                    complexities.append(complexity_value)
                if complexities:
                    avg_complexity = sum(complexities) / len(complexities)
                    return (avg_complexity, len(complexities))
            except Exception as exc:
                logging.debug('Failed to read complexity from %s: %s', path, exc)
        return (None, None)

    def read_all(self, args):
        self.master = self.read_value(args.cyclomatic_complexity_master)
        self.develop = self.read_value(args.cyclomatic_complexity_develop)
        self.feature_value = self.read_value(args.cyclomatic_complexity_feature)

    def format_value(self, value):
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

    def badge(self, value):
        return ''


class DocstringCoverageMetric(BaseMetric):
    key = 'docstring'
    label = 'Docstring coverage with interrogate'
    thresholds = [
        (90, '', 'brightgreen'),
        (70, '', 'yellow'),
        (50, '', 'orange'),
        (0, '', 'red'),
    ]
    reverse = False

    def __init__(self, badge_gen, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_value(self, path: str):
        if path and Path(path).exists():
            lines = Path(path).read_text(encoding='utf-8').splitlines()
            for line in lines:
                if line.startswith('| TOTAL'):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        percent = parts[-2].strip()
                        return percent
            # fallback: scan lines in reverse for "actual:"
            for line in reversed(lines):
                if 'actual:' in line:
                    after_actual = line.split('actual:')[-1].strip()
                    percent = after_actual.split()[0]
                    return percent
        return ''

    def read_all(self, args):
        self.master = self.read_value(args.coverage_docstring_master)
        self.develop = self.read_value(args.coverage_docstring_develop)
        self.feature_value = self.read_value(args.coverage_docstring_feature)

    def format_value(self, value):
        if not value:
            return '0%'
        return value

    def badge(self, value):
        return ''


# --- New Metric Subclasses for Github Workflow, CodeFactor, Codecov ---
class GithubWorkflowMetric(BaseMetric):
    """Branch statuses for a single GitHub workflow, driven by env
    vars.
    """

    def __init__(self, badge_gen, workflow_filename, label, feature=None):
        # Derive key from workflow filename: remove extension and
        # replace '.' and '_' with '-'.
        base = Path(workflow_filename).stem.replace('.', '-').replace('_', '-')
        key = base
        super().__init__(badge_gen, key=key, label=label, feature=feature)
        self.workflow_filename = workflow_filename

    @staticmethod
    def _env_key(base: str, branch: str) -> str:
        return f'CI_WORKFLOW_{base.upper().replace("-", "_")}_{branch.upper()}'

    def read_all(self, args):
        base = self.key
        self.master = os.environ.get(self._env_key(base, 'master'), '')
        self.develop = os.environ.get(self._env_key(base, 'develop'), '')
        self.feature_value = os.environ.get(self._env_key(base, 'feature'), '')

    def badge(self, value):
        return self.badge_gen.github_badge(self.workflow_filename, value)

    def refs(self):
        # Use badge_gen.github_workflows for URLs
        return {
            'master': self.badge('master'),
            'master_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
            'develop': self.badge('develop'),
            'develop_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
            'feature': self.badge(self.feature),
            'feature_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
        }


class CodeFactorMetric(BaseMetric):
    """CodeFactor letter grade across branches via env."""

    key = 'codefactor'
    label = 'Code quality from CodeFactor.io'

    def __init__(self, badge_gen, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_all(self, args):
        self.master = os.environ.get('CI_CODEFACTOR_MASTER', '')
        self.develop = os.environ.get('CI_CODEFACTOR_DEVELOP', '')
        self.feature_value = os.environ.get('CI_CODEFACTOR_FEATURE', '')

    def badge(self, value):
        return self.badge_gen.codefactor_badge(value)

    def refs(self):
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
    """Codecov unit test coverage percentage across branches via env."""

    key = 'codecov'
    label = 'Unit test coverage from Codecov.io'

    def __init__(self, badge_gen, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_all(self, args):
        self.master = os.environ.get('CI_CODECOV_MASTER', '')
        self.develop = os.environ.get('CI_CODECOV_DEVELOP', '')
        self.feature_value = os.environ.get('CI_CODECOV_FEATURE', '')


class LinesOfCodeMetric(BaseMetric):
    key = 'loc'
    label = 'Source/Logical lines of code'

    def __init__(self, badge_gen, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _sum_raw_metrics(path: Optional[str]) -> Optional[Tuple[int, int]]:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        sloc = 0
        lloc = 0

        def add_from(obj: Any):
            nonlocal sloc, lloc
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
                        add_from(v)
            elif isinstance(obj, list):
                for it in obj:
                    add_from(it)

        add_from(data)
        return (sloc, lloc)

    def read_all(self, args):
        self.master = self._sum_raw_metrics(getattr(args, 'raw_metrics_master', None))
        self.develop = self._sum_raw_metrics(getattr(args, 'raw_metrics_develop', None))
        self.feature_value = self._sum_raw_metrics(getattr(args, 'raw_metrics_feature', None))


class FileCountMetric(BaseMetric):
    key = 'files'
    label = 'Number of files'

    def __init__(self, badge_gen, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _count_files(path: Optional[str]) -> Optional[int]:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        if isinstance(data, dict):
            return len([k for k, v in data.items() if isinstance(v, list)])
        return None

    def read_all(self, args):
        self.master = self._count_files(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._count_files(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._count_files(
            getattr(args, 'cyclomatic_complexity_feature', None)
        )


class FunctionCountMetric(BaseMetric):
    key = 'funcs'
    label = 'Number of functions'

    def __init__(self, badge_gen, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _count_functions(path: Optional[str]) -> Optional[int]:
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

    def read_all(self, args):
        self.master = self._count_functions(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._count_functions(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._count_functions(
            getattr(args, 'cyclomatic_complexity_feature', None)
        )

    def badge(self, value):
        return self.badge_gen.codecov_badge(value)

    def refs(self):
        cc = self.badge_gen.codecov
        return {
            'master': self.badge('master'),
            'master_url': f'{cc}',
            'develop': self.badge('develop'),
            'develop_url': f'{cc}/branch/develop',
            'feature': self.badge(self.feature),
            'feature_url': f'{cc}/branch/{self.feature}',
        }


# file: badges/render.py
class HTMLDashboardRenderer:
    """Renders a dark, card-based HTML dashboard similar to the provided
    example.
    """

    CSS = """
    body {
      --base-size: clamp(18px, 1.5vw, 22px);
      font-family: nunito, ui-sans-serif, system-ui, -apple-system,
      BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial,
      "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji",
      "Segoe UI Symbol", "Noto Color Emoji";
      background-color: #262626;
      color: inherit;
      color-scheme: light dark;
      font-size: var(--base-size);
    }
    .card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(20em, 1fr));
      gap: 0;
      padding: 0;
      background-color: transparent;
      justify-content: start;
    }
    .card {
      border-radius: 0.3em;
      overflow: hidden;
      border: 1px solid #111;
      background-color: transparent;
      margin: 0.5em;
      display: flex;
      flex-direction: column;
    }
    .label {
      font-weight: 300;
      color: #ccc;
      display: flex;
      align-items: center;
      gap: 0.5em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      background-color: #202020;
      padding: 0.7em .7em;
      border-radius: 0;
      margin: 0;
      font-size: 1em;
    }
    .values {
      display: flex;
      flex-direction: column;
      font-weight: 300;
      gap: 0.5em;
      padding: 0.7em 0.7em;
      background-color: #1a1a1a;
      border-top: 1px solid #101010;
      font-size: 1em;
    }
    .values span img { vertical-align: middle; }
    .green { color: #6eb543; }
    .yellow-green { color: #9acd32; }
    .yellow { color: #e8b745; }
    .orange { color: #f39c12; }
    .red { color: #e46259; }
    .blue { color: #71b2f0; }
    .gray { color: #757575; }
    a { color: inherit; text-decoration: none; }
    """

    def __init__(self, metrics: List[BaseMetric], feature: str, badge_gen: 'BadgeGenerator'):
        self.metrics = metrics
        self.feature = feature
        self.badge_gen = badge_gen
        # quick lookup by metric key
        self.metric_by_key = {m.key: m for m in metrics}

    # --- Network helpers (best-effort; falls back to env if fails) ---
    @staticmethod
    def _fetch(url: str, timeout: float = 8.0) -> Optional[str]:
        try:
            # Only allow HTTPS to satisfy security lints
            if not (isinstance(url, str) and url.startswith('https://')):
                return None
            with urlopen(url, timeout=timeout) as resp:  # noqa: S310 - controlled HTTPS fetch
                if 200 <= resp.status < 300:
                    return resp.read().decode('utf-8', errors='ignore')
        except (URLError, HTTPError, TimeoutError) as exc:
            logging.debug('Fetch failed %s: %s', url, exc)
        except Exception as exc:  # pragma: no cover - resilience
            logging.debug('Fetch failed %s: %s', url, exc)
        return None

    def _github_badge_status(self, workflow: str, branch: Optional[str]) -> Optional[str]:
        url = self.badge_gen.github_workflow_badge_img(workflow, branch)
        svg = self._fetch(url)
        if not svg:
            return None
        # GitHub badge usually contains text like >passing< or >failing<
        m = re.search(r'>(passing|failing|cancelled|skipped|queued|in progress)<', svg, re.I)
        if not m:
            return None
        word = m.group(1).lower()
        if word == 'passing':
            return 'passed'
        if word == 'failing':
            return 'failed'
        if word in ('cancelled', 'skipped', 'queued', 'in progress'):
            return word
        return word

    def _codecov_percent(self, branch: Optional[str]) -> Optional[int]:
        """Fetch Codecov percent from the badge SVG.

        Uses CODECOV_REPO if set; otherwise falls back to the configured
        repo. Parses only percent values inside text nodes (avoids
        width="100%" etc.).
        """
        token = os.environ.get('CODECOV_TOKEN', 'qtsB5Q5BXO')
        repo = os.environ.get('CODECOV_REPO', self.badge_gen.repo)
        if branch and branch not in ('', 'master'):
            url = f'https://codecov.io/gh/{repo}/branch/{branch}/graph/badge.svg?token={token}'
        else:
            url = f'https://codecov.io/gh/{repo}/graph/badge.svg?token={token}'
        svg = self._fetch(url)
        if not svg:
            return None
        # Find percentages that appear as text content: >72%< etc.
        matches = re.findall(r'>\s*(\d+(?:\.\d+)?)%\s*<', svg)
        if not matches:
            return None
        try:
            val = float(matches[-1])
            return int(round(val))
        except Exception:
            return None

    def _codefactor_grade(self, branch: str) -> Optional[str]:
        url = self.badge_gen.codefactor_badge_img(branch)
        svg = self._fetch(url)
        if not svg:
            return None
        m = re.search(r'>([A-F])<', svg)
        if not m:
            return None
        return m.group(1)

    @staticmethod
    def _grade_color_for_letter(letter: str) -> str:
        letter = (letter or '').upper()
        if letter == 'A':
            return 'green'
        if letter == 'B':
            return 'yellow-green'
        if letter == 'C':
            return 'yellow'
        if letter == 'D':
            return 'orange'
        if letter in ('E', 'F'):
            return 'red'
        return 'gray'

    @staticmethod
    def _color_for_percent(p: Optional[float]) -> str:
        if p is None:
            return 'gray'
        # Coverage thresholds:
        #  - A >= 90 (green)
        #  - B >= 75 (yellow-green)
        #  - C >= 60 (yellow)
        #  - D >= 40 (orange)
        #  - F < 40 (red)
        if p >= 90:
            return 'green'
        if p >= 75:
            return 'yellow-green'
        if p >= 60:
            return 'yellow'
        if p >= 40:
            return 'orange'
        return 'red'

    @staticmethod
    def _complexity_grade_color(avg: Optional[float]) -> Tuple[str, str]:
        if avg is None:
            return ('?', 'gray')
        # thresholds (lower is better):
        # A 1–5, B 6–10, C 11–20, D 21–40, F 41+
        if avg <= 5:
            return ('A', 'green')
        if avg <= 10:
            return ('B', 'yellow-green')
        if avg <= 20:
            return ('C', 'yellow')
        if avg <= 40:
            return ('D', 'orange')
        return ('F', 'red')

    def _status_text_for_metric(self, key: str, branch: str) -> Optional[Tuple[str, str]]:  # noqa: C901
        """Return (text, color-class) if we can render text status, else
        None to use badges.
        """
        m = self.metric_by_key.get(key)
        if not m:
            return None
        value = getattr(
            m,
            'master'
            if branch == 'master'
            else ('develop' if branch == 'develop' else 'feature_value'),
            None,
        )

        # Docstring coverage: expects like "35%"
        if isinstance(m, DocstringCoverageMetric):
            if not value:
                return ('no status yet', 'gray')
            try:
                p = float(str(value).strip().rstrip('%'))
            except Exception:
                p = None
            color = self._color_for_percent(p)
            text = f'{int(round(p))}%' if p is not None else 'unknown'
            return (text, color)

        # Maintainability: (avg_mi, count)
        if isinstance(m, MaintainabilityMetric):
            if not value or not isinstance(value, tuple) or value[0] is None:
                return ('unknown', 'gray')
            mi = float(value[0])
            # Maintainability index thresholds:
            #  - A 80–100, B 60–79, C 40–59,
            #  - D 20–39, F 0–19
            if mi >= 80:
                grade = 'A'
                color = 'green'
            elif mi >= 60:
                grade = 'B'
                color = 'yellow-green'
            elif mi >= 40:
                grade = 'C'
                color = 'yellow'
            elif mi >= 20:
                grade = 'D'
                color = 'orange'
            else:
                grade = 'F'
                color = 'red'
            text = f'{grade} ({int(round(mi))})'
            return (text, color)

        # Complexity: (avg, count)
        if isinstance(m, ComplexityMetric):
            if not value or not isinstance(value, tuple) or value[0] is None:
                return ('unknown', 'gray')
            avg = float(value[0])
            grade, color = self._complexity_grade_color(avg)
            text = f'{grade} ({avg:.1f})'
            return (text, color)

        # Codecov: try fetch badge percent; fallback to env
        if isinstance(m, CodecovMetric):
            # For master/develop: do not fetch from Codecov
            # unless provided via env
            if branch in ('master', 'develop'):
                val = value
                if not val:
                    return ('no status yet', 'gray')
                try:
                    p = int(round(float(str(val).strip().rstrip('%'))))
                except Exception:
                    return ('unknown', 'gray')
                color = self._color_for_percent(float(p))
                return (f'{p}%', color)

            # Feature branch: fetch from Codecov badge; fallback to env
            branch_for_badge = self.feature
            p = self._codecov_percent(branch_for_badge)
            if p is None:
                val = value
                if val:
                    try:
                        p = int(round(float(str(val).strip().rstrip('%'))))
                    except Exception:
                        p = None
            if p is None:
                return ('unknown', 'gray')
            color = self._color_for_percent(float(p))
            return (f'{p}%', color)

        # CodeFactor: try fetch letter grade; fallback to env
        if isinstance(m, CodeFactorMetric):
            branch_for_badge = self.feature if branch == 'feature' else branch
            letter = self._codefactor_grade(branch_for_badge)
            if letter is None:
                letter = str(value or '').strip().upper()
            if not letter:
                return ('unknown', 'gray')
            return (letter, self._grade_color_for_letter(letter))

        # GitHub workflows: try fetch status; fallback to env
        if isinstance(m, GithubWorkflowMetric):
            if branch == 'master':
                branch_for_badge = None
            elif branch == 'feature':
                branch_for_badge = self.feature
            else:
                branch_for_badge = 'develop'
            status = self._github_badge_status(m.workflow_filename, branch_for_badge)
            if status is None:
                status = str(value or '').strip().lower()
            if status in ('success', 'succeeded', 'pass', 'passed', 'passing', 'ok'):
                return ('passed', 'green')
            if status in ('fail', 'failed', 'failing', 'error', 'cancelled'):
                return ('failed', 'red')
            if status in ('-', '', 'unknown', 'no status', 'no status yet'):
                return ('no status yet', 'gray')
            return (status, 'gray')

        # Size metrics: always blue, formatted with thousands separators
        def _fmt_int(v) -> Optional[str]:
            if v in (None, ''):
                return None
            try:
                return f'{int(str(v).replace(",", "").strip()):,}'
            except Exception:
                return None

        if isinstance(m, (FileCountMetric, FunctionCountMetric)):
            formatted = _fmt_int(value)
            if formatted is None:
                return ('-', 'gray')
            return (formatted, 'blue')

        if isinstance(m, LinesOfCodeMetric):
            tup = value if isinstance(value, tuple) else None
            if not tup:
                return ('-', 'gray')
            sloc, lloc = tup
            s = _fmt_int(sloc) or '-'
            lloc_str = _fmt_int(lloc) or '-'
            ratio: Optional[float] = None
            try:
                if lloc and int(str(lloc).replace(',', '').strip()) > 0:
                    ratio = float(sloc) / float(lloc)
            except Exception:
                ratio = None
            if ratio is None:
                return (f'{s}/{lloc_str}', 'gray')
            # Ratio thresholds:
            #  - A <= 1.0 green
            #  - B <= 1.1 yellow-green
            #  - C <= 1.25 yellow
            #  - D <= 1.5 orange
            #  - F > 1.5 red
            if ratio <= 1.0:
                color = 'green'
            elif ratio <= 1.1:
                color = 'yellow-green'
            elif ratio <= 1.25:
                color = 'yellow'
            elif ratio <= 1.5:
                color = 'orange'
            else:
                color = 'red'
            return (f'{ratio:.2f} ({s}/{lloc_str})', color)

        return ('unknown', 'gray')

    def _value_item_html(self, key: str, branch: str, branch_label: str) -> str:
        # Prefer derived text (from fetched badge SVGs or env fallbacks)
        status = self._status_text_for_metric(key, branch)
        if status is not None:
            text, color = status
            return f'<span class="{color}">{branch_label}: {text}</span>'

        # Fallback to unknown
        return f'<span class="gray">{branch_label}: no status yet</span>'

    def _card_html(self, title: str, icon_class: str, key: str) -> str:
        # Feature branch label
        feature_label = self.feature
        values_html = '\n'.join([
            self._value_item_html(key, 'master', 'master'),
            self._value_item_html(key, 'develop', 'develop'),
            self._value_item_html(key, 'feature', feature_label),
        ])
        return (
            f'<div class="card">\n'
            f'  <div class="label"><i class="{icon_class}"></i>{title}</div>\n'
            f'  <div class="values">\n{values_html}\n  </div>\n'
            f'</div>'
        )

    def render(self) -> str:
        # Group metrics into sections similar to the example
        groups: List[Tuple[str, str, List[str]]] = [
            ('Tests', 'fas fa-vial', ['test-code', 'test-tutorials', 'test-package-pypi']),
            ('Code Quality', 'fas fa-gauge', ['codefactor', 'maintainability', 'complexity']),
            ('Size', 'fas fa-file-code', ['loc', 'files', 'funcs']),
            ('Coverage', 'fas fa-square-poll-vertical', ['codecov', 'docstring']),
            ('Security', 'fas fa-lock', ['scan-security']),
            ('Build & Release', 'fas fa-rocket', ['build-docs', 'publish-pypi']),
        ]

        # Build cards for all keys that exist in badge_sets/metrics
        cards: List[str] = []
        for _group_title, icon, keys in groups:
            for key in keys:
                m = self.metric_by_key.get(key)
                if not m:
                    continue
                cards.append(self._card_html(m.label, icon, key))

        # Include any additional metrics not covered above
        covered = {k for _, _, ks in groups for k in ks}
        for m in self.metrics:
            if m.key not in covered:
                # Choose a reasonable default icon
                icon = 'fas fa-gauge'
                cards.append(self._card_html(m.label, icon, m.key))

        cards_html = '\n'.join(cards)

        html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Dashboard</title>
  <style>
{self.CSS}
  </style>
  <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css\">
</head>
<body>

<div class=\"card-grid\">
{cards_html}
</div>

</body>
</html>
"""
        return html


class HTMLDashboardRendererWithSpec(HTMLDashboardRenderer):
    """Renderer variant that uses an explicit, ordered card spec.

    The spec is a list of tuples: (metric_key, label, icon_class).
    """

    def __init__(
        self,
        metrics: List[BaseMetric],
        feature: str,
        badge_gen: 'BadgeGenerator',
        cards_spec: List[tuple[str, str, str]],
    ) -> None:
        super().__init__(metrics, feature, badge_gen)
        self.cards_spec = cards_spec

    def render(self) -> str:
        cards: List[str] = []
        for key, title, icon in self.cards_spec:
            m = self.metric_by_key.get(key)
            if not m:
                # If key not found (e.g., typo), skip silently
                continue
            # Use the title provided by spec (already set on metric), but prefer spec
            cards.append(self._card_html(title or m.label, icon, key))

        cards_html = '\n'.join(cards)

        html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Dashboard</title>
  <style>
{self.CSS}
  </style>
  <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css\">
  </head>
  <body>

  <div class=\"card-grid\">
  {cards_html}
  </div>

  </body>
  </html>
"""
        return html


def _detect_feature_branch() -> str:
    """Detect feature branch for CI and local runs (best effort)."""
    # Prefer CI_BRANCH, then GitHub refs, else fallback.
    return (
        os.environ.get('CI_BRANCH')
        or os.environ.get('GITHUB_REF_NAME')
        or os.environ.get('GITHUB_HEAD_REF')
        or 'unknown'
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments and hydrate inputs from .badgery.yaml.

    The CLI still accepts basic flags, but card definitions, grouping,
    workflow filenames, and report file patterns are read from
    `.badgery.yaml` in the current working directory.
    """
    parser = argparse.ArgumentParser(
        description='Generate an HTML dashboard of status badges for diffraction-lib.'
    )
    parser.add_argument(
        '--output',
        default='BADGES.html',
        help='Output HTML file (default: BADGES.html)',
    )
    parser.add_argument(
        '--repo',
        required=True,
        help='GitHub repository, e.g. easyscience/diffraction-lib (required)',
    )
    parser.add_argument(
        '--branch',
        required=True,
        help='Feature branch name to display (required)',
    )
    parser.add_argument(
        '--config',
        default='.badgery.yaml',
        help='Path to configuration file (default: .badgery.yaml)',
    )
    parser.add_argument(
        '--log-level',
        default=os.environ.get('BADGES_LOG_LEVEL', 'INFO'),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging verbosity (default: INFO)',
    )
    # No style/shields options; dashboard is pure HTML text.
    args = parser.parse_args()

    # Load config and resolve report paths
    cards = _load_cards_from_yaml(args.config)
    args.cards_config = cards

    # Resolve report path patterns into per-branch files
    feature_branch = args.branch

    # Collect patterns per kind
    complexity_pattern = None
    maintainability_pattern = None
    raw_pattern = None
    docstring_pattern = None

    for card in cards:
        if not card.get('enabled', True):
            continue
        ctype = str(card.get('type', '')).strip().lower()
        # Accept synonyms/typos from config
        if ctype in {'radon_cc'}:
            complexity_pattern = card.get('report') or card.get('dir') or complexity_pattern
        if ctype in {'radon_files', 'radon_funcs'}:
            # both use the cyclomatic-complexity report as input
            complexity_pattern = card.get('report') or card.get('dir') or complexity_pattern
        if ctype in {'radon_mi'}:
            maintainability_pattern = card.get('report') or maintainability_pattern
        if ctype in {'radon_loc'}:
            raw_pattern = card.get('report') or raw_pattern
        if ctype in {'interrogate'}:
            docstring_pattern = card.get('report') or docstring_pattern

    def _resolve(pattern: Optional[str], branch: str) -> Optional[str]:
        if not pattern:
            return None
        # If pattern contains the special "**" placeholder, treat it as the branch name placeholder.
        candidate = pattern.replace('**', branch)
        p = Path(candidate)
        if p.exists():
            return str(p)
        # As a fallback, try globbing in case pattern contains * wildcards
        matches = glob(candidate)
        if matches:
            return matches[0]
        return None

    # Populate args expected by metrics
    args.cyclomatic_complexity_master = _resolve(complexity_pattern, 'master') or os.environ.get('CI_COMPLEXITY_MASTER')
    args.cyclomatic_complexity_develop = _resolve(complexity_pattern, 'develop') or os.environ.get('CI_COMPLEXITY_DEVELOP')
    args.cyclomatic_complexity_feature = _resolve(complexity_pattern, feature_branch) or os.environ.get('CI_COMPLEXITY_FEATURE')

    args.maintainability_index_master = _resolve(maintainability_pattern, 'master') or os.environ.get('CI_MAINTAINABILITY_MASTER')
    args.maintainability_index_develop = _resolve(maintainability_pattern, 'develop') or os.environ.get('CI_MAINTAINABILITY_DEVELOP')
    args.maintainability_index_feature = _resolve(maintainability_pattern, feature_branch) or os.environ.get('CI_MAINTAINABILITY_FEATURE')

    args.raw_metrics_master = _resolve(raw_pattern, 'master') or os.environ.get('CI_RAW_METRICS_MASTER')
    args.raw_metrics_develop = _resolve(raw_pattern, 'develop') or os.environ.get('CI_RAW_METRICS_DEVELOP')
    args.raw_metrics_feature = _resolve(raw_pattern, feature_branch) or os.environ.get('CI_RAW_METRICS_FEATURE')

    args.coverage_docstring_master = _resolve(docstring_pattern, 'master') or os.environ.get('CI_DOCSTRING_MASTER')
    args.coverage_docstring_develop = _resolve(docstring_pattern, 'develop') or os.environ.get('CI_DOCSTRING_DEVELOP')
    args.coverage_docstring_feature = _resolve(docstring_pattern, feature_branch) or os.environ.get('CI_DOCSTRING_FEATURE')

    return args


# file: make_badges.py
METRIC_SPECS: list = []  # dynamically constructed from .badgery.yaml

BRANCHES = ['master', 'develop', 'feature']


def main() -> None:
    args = parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level))

    feature = args.branch
    badge_gen = BadgeGenerator(repo=args.repo)

    # Build metrics and card specs from config
    metrics, cards_spec = _build_metrics_from_config(args.cards_config, badge_gen, feature)

    # Read all values for each metric
    for metric in metrics:
        try:
            metric.read_all(args)
        except Exception as exc:
            logging.debug('Metric read failed for %s: %s', getattr(metric, 'key', '?'), exc)

    renderer = HTMLDashboardRendererWithSpec(metrics, feature, badge_gen, cards_spec)
    html = renderer.render()
    Path(args.output).write_text(html, encoding='utf-8')


# --- Configuration loading and mapping ---

def _load_cards_from_yaml(path: str) -> list[dict[str, Any]]:
    """Minimal YAML loader tailored for the simple `.badgery.yaml` structure.

    Supports only a top-level `cards:` list, where each item is a flat
    mapping of simple scalars: `group`, `type`, `title`, `workflow`/`file`,
    `report`/`dir`, and `enabled`.
    """
    p = Path(path)
    if not p.exists():
        logging.info('Config %s not found; using empty card list', path)
        return []
    lines = p.read_text(encoding='utf-8').splitlines()
    items: list[dict[str, Any]] = []
    in_cards = False
    current: Optional[dict[str, Any]] = None
    current_indent = 0
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.strip().startswith('#'):
            continue
        if not in_cards:
            if line.strip() == 'cards:':
                in_cards = True
                continue
            else:
                continue
        # We are inside the cards list
        # New item
        if line.lstrip().startswith('- '):
            current = {}
            items.append(current)
            # track indent of this dash
            current_indent = len(line) - len(line.lstrip())
            continue
        # Key: value lines belonging to the current item
        if current is None:
            continue
        # Only accept lines indented beyond the dash indent
        indent = len(line) - len(line.lstrip())
        if indent <= current_indent:
            # outside current item; ignore
            continue
        # Parse key: value
        if ':' not in line:
            continue
        key, val = line.strip().split(':', 1)
        val = val.strip()
        # Convert booleans
        if val.lower() in ('true', 'false'):
            current[key] = (val.lower() == 'true')
        else:
            # Unquote if surrounded by quotes
            if (val.startswith("'") and val.endswith("'")) or (
                val.startswith('"') and val.endswith('"')
            ):
                val = val[1:-1]
            current[key] = val
    return items


def _group_icon(group: str) -> str:
    g = (group or '').strip().lower()
    mapping = {
        'tests': 'fas fa-vial',
        'code quality': 'fas fa-gauge',
        'size': 'fas fa-file-code',
        'coverage': 'fas fa-square-poll-vertical',
        'security': 'fas fa-lock',
        'build & release': 'fas fa-rocket',
        'publish to pypi': 'fas fa-box',
    }
    if g in mapping:
        return mapping[g]
    # Heuristic fallback by keyword
    if 'test' in g:
        return 'fas fa-vial'
    if 'qualit' in g:
        return 'fas fa-gauge'
    if 'size' in g:
        return 'fas fa-file-code'
    if 'cover' in g:
        return 'fas fa-square-poll-vertical'
    if 'secur' in g:
        return 'fas fa-lock'
    if 'build' in g or 'release' in g:
        return 'fas fa-rocket'
    if 'pypi' in g or 'publish' in g:
        return 'fas fa-box'
    return 'fas fa-gauge'


def _build_metrics_from_config(cards: list[dict[str, Any]], badge_gen: 'BadgeGenerator', feature: str):
    """Create metric instances and a card rendering spec from config.

    Returns (metrics, cards_spec) where cards_spec is a list of tuples:
    (metric_key, label, icon_class).
    """
    metrics: list[BaseMetric] = []
    cards_spec: list[tuple[str, str, str]] = []

    # Reuse singletons for non-workflow metrics
    singleton_by_type: dict[str, BaseMetric] = {}

    def _get_or_create(ctype: str) -> Optional[BaseMetric]:
        if ctype in singleton_by_type:
            return singleton_by_type[ctype]
        inst: Optional[BaseMetric] = None
        if ctype == 'codefactor':
            inst = CodeFactorMetric(badge_gen, feature=feature)
        elif ctype == 'codecov':
            inst = CodecovMetric(badge_gen, feature=feature)
        elif ctype == 'radon_mi':
            inst = MaintainabilityMetric(badge_gen, feature=feature)
        elif ctype == 'radon_cc':
            inst = ComplexityMetric(badge_gen, feature=feature)
        elif ctype == 'radon_loc':
            inst = LinesOfCodeMetric(badge_gen, feature=feature)
        elif ctype == 'radon_files':
            inst = FileCountMetric(badge_gen, feature=feature)
        elif ctype == 'radon_funcs':
            inst = FunctionCountMetric(badge_gen, feature=feature)
        elif ctype == 'interrogate':
            inst = DocstringCoverageMetric(badge_gen, feature=feature)
        if inst is not None:
            singleton_by_type[ctype] = inst
        return inst

    for card in cards:
        if not card.get('enabled', True):
            continue
        ctype = str(card.get('type', '')).strip().lower()
        title = card.get('title') or ''
        group = card.get('group') or ''
        icon = _group_icon(group)

        if ctype == 'gh_action':
            workflow = card.get('workflow') or card.get('file')
            if not workflow:
                logging.debug('Skipping gh_action without workflow/file in card %s', card)
                continue
            metric = GithubWorkflowMetric(badge_gen, workflow_filename=str(workflow), label=title, feature=feature)
            metrics.append(metric)
            # Derive key same way as metric does
            key = Path(str(workflow)).stem.replace('.', '-').replace('_', '-')
            cards_spec.append((key, title, icon))
            continue

        metric = _get_or_create(ctype)
        if metric is None:
            logging.debug('Unknown card type %r; skipping', ctype)
            continue
        # Override label/title on the metric instance for display
        if title:
            metric.label = title
        # Register metric once
        if metric not in metrics:
            metrics.append(metric)
        cards_spec.append((metric.key, metric.label or title, icon))

    return metrics, cards_spec


if __name__ == '__main__':
    main()
