# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""HTML rendering for the Badgery dashboard."""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING
from typing import List
from typing import Optional
from typing import Tuple
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import urlopen

from badgery.metrics import BaseMetric
from badgery.metrics import CodecovMetric
from badgery.metrics import CodeFactorMetric
from badgery.metrics import ComplexityMetric
from badgery.metrics import DocstringCoverageMetric
from badgery.metrics import FileCountMetric
from badgery.metrics import FunctionCountMetric
from badgery.metrics import GithubWorkflowMetric
from badgery.metrics import LinesOfCodeMetric
from badgery.metrics import MaintainabilityMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


class HTMLDashboardRenderer:
    """Render metrics into a compact HTML dashboard."""

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

    def __init__(
        self,
        metrics: List[BaseMetric],
        feature: str,
        badge_gen: 'BadgeGenerator',
        default_branch: str = 'master',
        develop_branch: str = 'develop',
    ):
        """Initialize renderer with metrics and branch labels."""
        self.metrics = metrics
        self.feature = feature
        self.badge_gen = badge_gen
        self.metric_by_key = {m.key: m for m in metrics}
        self.default_branch = default_branch
        self.develop_branch = develop_branch

    @staticmethod
    def _fetch(url: str, timeout: float = 8.0) -> Optional[str]:
        """Fetch a URL and return its text content.

        Args:
            url: HTTPS URL to fetch.
            timeout: Socket timeout in seconds.

        Returns:
            The response body decoded as UTF-8, or ``None`` on
            any error.
        """
        try:
            if not (isinstance(url, str) and url.startswith('https://')):
                return None
            with urlopen(url, timeout=timeout) as resp:  # noqa: S310
                if 200 <= resp.status < 300:
                    return resp.read().decode('utf-8', errors='ignore')
        except (URLError, HTTPError, TimeoutError) as exc:
            logging.debug('Fetch failed %s: %s', url, exc)
        except Exception as exc:
            logging.debug('Fetch failed %s: %s', url, exc)
        return None

    def _github_badge_status(self, workflow: str, branch: Optional[str]) -> Optional[str]:
        """Parse a GitHub Actions badge and return a normalized status.

        Args:
            workflow: Workflow filename, e.g. ``ci.yml``.
            branch: Optional branch name to include in the badge URL.

        Returns:
            One of: ``passed``, ``failed``, ``queued``, ``cancelled``,
            ``skipped``, ``in progress``, or ``None`` if the badge
            cannot be parsed.
        """
        url = self.badge_gen.github_workflow_badge_img(workflow, branch)
        svg = self._fetch(url)
        if not svg:
            return None
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
        """Return Codecov percentage for a branch by parsing the badge.

        Args:
            branch: Optional branch; ``None`` / ``master`` resolve to
                the default graph.

        Returns:
            Integer percentage rounded to nearest whole number, or
            ``None``.
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
        matches = re.findall(r'>\s*(\d+(?:\.\d+)?)%\s*<', svg)
        if not matches:
            return None
        try:
            val = float(matches[-1])
            return int(round(val))
        except Exception:
            return None

    def _codefactor_grade(self, branch: str) -> Optional[str]:
        """Return a CodeFactor letter grade parsed from the badge.

        Returns:
            Optional[str]: Letter grade ``A``–``F`` or ``None``.
        """
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
        """Map a CodeFactor letter grade to a color class name.

        Returns:
            str: Color class name.
        """
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
        """Map a percentage to a color class name.

        Returns:
            str: Color class name.
        """
        if p is None:
            return 'gray'
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
        """Map average cyclomatic complexity to a (grade, color).

        Returns:
            tuple[str, str]: Grade letter and color class.
        """
        if avg is None:
            return ('?', 'gray')
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
        """Return normalized status text and color for a metric/branch.

        Args:
            key: Metric key, e.g. ``codecov``.
            branch: One of ``master``, ``develop``, or ``feature``.

        Returns:
            tuple[str, str]: ``(text, color)`` or
            ``('unknown', 'gray')``.
        """
        m = self.metric_by_key.get(key)
        if not m:
            return None
        attr = (
            'master'
            if branch == 'master'
            else ('develop' if branch == 'develop' else 'feature_value')
        )
        value = getattr(m, attr, None)

        if isinstance(m, DocstringCoverageMetric):
            if not value:
                return ('unknown', 'gray')
            try:
                p = float(str(value).strip().rstrip('%'))
            except Exception:
                p = None
            color = self._color_for_percent(p)
            text = f'{int(round(p))}%' if p is not None else 'unknown'
            return (text, color)

        if isinstance(m, MaintainabilityMetric):
            if not value or not isinstance(value, tuple) or value[0] is None:
                return ('unknown', 'gray')
            mi = float(value[0])
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

        if isinstance(m, ComplexityMetric):
            if not value or not isinstance(value, tuple) or value[0] is None:
                return ('unknown', 'gray')
            avg = float(value[0])
            grade, color = self._complexity_grade_color(avg)
            text = f'{grade} ({avg:.1f})'
            return (text, color)

        if isinstance(m, CodecovMetric):
            if branch in ('master', 'develop'):
                val = value
                if not val:
                    return ('unknown', 'gray')
                try:
                    p = int(round(float(str(val).strip().rstrip('%'))))
                except Exception:
                    return ('unknown', 'gray')
                color = self._color_for_percent(float(p))
                return (f'{p}%', color)

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

        if isinstance(m, CodeFactorMetric):
            if branch == 'master':
                branch_for_badge = self.default_branch
            elif branch == 'develop':
                branch_for_badge = self.develop_branch
            else:
                branch_for_badge = self.feature
            letter = self._codefactor_grade(branch_for_badge)
            if letter is None:
                letter = str(value or '').strip().upper()
            if not letter:
                return ('unknown', 'gray')
            return (letter, self._grade_color_for_letter(letter))

        if isinstance(m, GithubWorkflowMetric):
            if branch == 'master':
                branch_for_badge = None
            elif branch == 'feature':
                branch_for_badge = self.feature
            else:
                branch_for_badge = self.develop_branch
            status = self._github_badge_status(m.workflow_filename, branch_for_badge)
            if status is None:
                status = str(value or '').strip().lower()
            if status in ('success', 'succeeded', 'pass', 'passed', 'passing', 'ok'):
                return ('passed', 'green')
            if status in ('fail', 'failed', 'failing', 'error', 'cancelled'):
                return ('failed', 'red')
            if status in ('-', '', 'unknown', 'no status', 'no status yet'):
                return ('unknown', 'gray')
            return (status, 'gray')

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
        """Render a single metric status span for a given branch.

        Returns:
            str: HTML span element.
        """
        status = self._status_text_for_metric(key, branch)
        if status is not None:
            text, color = status
            return f'<span class="{color}">{branch_label}: {text}</span>'
        return f'<span class="gray">{branch_label}: unknown</span>'

    def _card_html(self, title: str, icon_class: str, key: str) -> str:
        """Render a complete metric card HTML block.

        Returns:
            str: HTML block for a metric card.
        """
        feature_label = self.feature
        values_html = '\n'.join([
            self._value_item_html(key, 'master', self.default_branch),
            self._value_item_html(key, 'develop', self.develop_branch),
            self._value_item_html(key, 'feature', feature_label),
        ])
        return (
            f'<div class="card">\n'
            f'  <div class="label"><i class="{icon_class}"></i>{title}</div>\n'
            f'  <div class="values">\n{values_html}\n  </div>\n'
            f'</div>'
        )

    def render(self) -> str:
        """Return the rendered HTML string for the dashboard."""
        return ''


class HTMLDashboardRendererWithSpec(HTMLDashboardRenderer):
    """Renderer variant that uses an explicit card order spec."""

    def __init__(
        self,
        metrics: List[BaseMetric],
        feature: str,
        badge_gen: 'BadgeGenerator',
        cards_spec: List[tuple[str, str, str]],
        default_branch: str = 'master',
        develop_branch: str = 'develop',
    ):
        """Initialize with context and ordered card spec."""
        super().__init__(
            metrics,
            feature,
            badge_gen,
            default_branch=default_branch,
            develop_branch=develop_branch,
        )
        self.cards_spec = cards_spec

    def render(self) -> str:
        """Return rendered HTML using the card spec order."""
        cards: List[str] = []
        for key, title, icon in self.cards_spec:
            m = self.metric_by_key.get(key)
            if not m:
                continue
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
