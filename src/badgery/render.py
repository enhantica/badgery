# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""HTML rendering for the Badgery dashboard."""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING
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
      grid-template-columns: repeat(auto-fit, minmax(17em, 1fr));
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
      margin: 0.75em;
      display: flex;
      flex-direction: column;
    }
    .card-title {
      font-weight: 300;
      color: #ccc;
      display: flex;
      align-items: center;
      gap: 0.75em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      background-color: #202020;
      padding: 1em 1em;
      border-radius: 0;
      margin: 0;
      font-size: 1em;
    }
    .values {
      display: flex;
      flex-direction: column;
      font-weight: 300;
      gap: 0.5em;
      padding: 1em 1em;
      background-color: #1a1a1a;
      border-top: 1px solid #101010;
      font-size: 1em;
    }
    .values .row {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 1em;
      min-width: 0;
    }
    .values .item-label {
      color: #ccc;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
    }
    /* Allow label color classes to take effect over base label color */
    .values .item-label.green { color: #6eb543; }
    .values .item-label.yellow-green { color: #b4cd32; }
    .values .item-label.yellow { color: #e8b745; }
    .values .item-label.orange { color: #f39c12; }
    .values .item-label.red { color: #e46259; }
    .values .item-label.blue { color: #71b2f0; }
    .values .item-label.gray { color: #757575; }
    /* Icons inherit label color so they colorize accordingly */
    .values .item-label .icon { color: currentColor; margin-right: 0.5em; }
    .values .item-value {
      white-space: nowrap;
    }
    .values span img { vertical-align: middle; }
    .green { color: #6eb543; }
    .yellow-green { color: #b4cd32; }
    .yellow { color: #e8b745; }
    .orange { color: #f39c12; }
    .red { color: #e46259; }
    .blue { color: #71b2f0; }
    .gray { color: #757575; }
    a { color: inherit; text-decoration: none; }
    """

    # HTTP ok status range
    OK_LOWER = 200
    OK_UPPER = 300

    # Percent thresholds
    PCT_GREEN = 90
    PCT_YELLOW_GREEN = 75
    PCT_YELLOW = 60
    PCT_ORANGE = 40

    # Complexity thresholds
    CC_A = 5
    CC_B = 10
    CC_C = 20
    CC_D = 40

    # Maintainability thresholds
    MI_A = 80
    MI_B = 60
    MI_C = 40
    MI_D = 20

    # SLOC/LLOC ratio thresholds
    RATIO_GREEN = 1.0
    RATIO_YELLOW_GREEN = 1.1
    RATIO_YELLOW = 1.25
    RATIO_ORANGE = 1.5

    def __init__(
        self,
        metrics: list[BaseMetric],
        feature: str,
        badge_gen: BadgeGenerator,
        default_branch: str = 'master',
        develop_branch: str = 'develop',
    ) -> None:
        """Initialize renderer with metrics and branch labels."""
        self.metrics = metrics
        self.feature = feature
        self.badge_gen = badge_gen
        self.metric_by_key = {m.key: m for m in metrics}
        self.default_branch = default_branch
        self.develop_branch = develop_branch

    @staticmethod
    def _fetch(url: str, timeout: float = 8.0) -> str | None:
        """Fetch a URL and return its text content.

        Args:
            url: HTTPS URL to fetch.
            timeout: Socket timeout in seconds.

        Returns:
            The response body decoded as UTF-8, or ``None`` on
            any error.
        """
        if not (isinstance(url, str) and url.startswith('https://')):
            return None
        resp = None
        try:
            resp = urlopen(url, timeout=timeout)  # noqa: S310
            status = getattr(resp, 'status', HTMLDashboardRenderer.OK_LOWER)
            if HTMLDashboardRenderer.OK_LOWER <= status < HTMLDashboardRenderer.OK_UPPER:
                data = resp.read()
                return data.decode('utf-8', errors='ignore')
        except (URLError, HTTPError, TimeoutError) as exc:
            logging.debug('Fetch failed %s: %s', url, exc)
        except Exception as exc:
            logging.debug('Fetch failed %s: %s', url, exc)
        finally:
            try:
                if resp and hasattr(resp, 'close'):
                    resp.close()
            except Exception as close_exc:
                logging.debug('Response close failed: %s', close_exc)
        return None

    def _github_badge_status(self, workflow: str, branch: str | None) -> str | None:
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
        if word in {'cancelled', 'skipped', 'queued', 'in progress'}:
            return word
        return word

    def _codecov_percent(self, branch: str | None) -> int | None:
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
        if branch and branch not in {'', 'master'}:
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
            return round(val)
        except Exception:
            return None

    def _codefactor_grade(self, branch: str) -> str | None:
        """Return a CodeFactor letter grade parsed from the badge.

        Returns:
            Optional[str]: Letter grade ``A``-``F`` or ``None``.
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
        if letter in {'E', 'F'}:
            return 'red'
        return 'gray'

    @staticmethod
    def _color_for_percent(p: float | None) -> str:
        """Map a percentage to a color class name.

        Returns:
            str: Color class name.
        """
        if p is None:
            return 'gray'
        if p >= HTMLDashboardRenderer.PCT_GREEN:
            return 'green'
        if p >= HTMLDashboardRenderer.PCT_YELLOW_GREEN:
            return 'yellow-green'
        if p >= HTMLDashboardRenderer.PCT_YELLOW:
            return 'yellow'
        if p >= HTMLDashboardRenderer.PCT_ORANGE:
            return 'orange'
        return 'red'

    @staticmethod
    def _complexity_grade_color(avg: float | None) -> tuple[str, str]:
        """Map average cyclomatic complexity to a (grade, color).

        Returns:
            tuple[str, str]: Grade letter and color class.
        """
        if avg is None:
            return ('?', 'gray')
        if avg <= HTMLDashboardRenderer.CC_A:
            return ('A', 'green')
        if avg <= HTMLDashboardRenderer.CC_B:
            return ('B', 'yellow-green')
        if avg <= HTMLDashboardRenderer.CC_C:
            return ('C', 'yellow')
        if avg <= HTMLDashboardRenderer.CC_D:
            return ('D', 'orange')
        return ('F', 'red')

    # Helpers broken out to reduce complexity of dispatcher below
    def _status_docstring(self, value: object) -> tuple[str, str]:
        if not value:
            return ('unknown', 'gray')
        try:
            p = float(str(value).strip().rstrip('%'))
        except Exception:
            p = None
        color = self._color_for_percent(p)
        text = f'{round(p)}%' if p is not None else 'unknown'
        return (text, color)

    @staticmethod
    def _status_maintainability(value: object) -> tuple[str, str]:
        if not value or not isinstance(value, tuple) or value[0] is None:
            return ('unknown', 'gray')
        mi = float(value[0])
        if mi >= HTMLDashboardRenderer.MI_A:
            grade, color = 'A', 'green'
        elif mi >= HTMLDashboardRenderer.MI_B:
            grade, color = 'B', 'yellow-green'
        elif mi >= HTMLDashboardRenderer.MI_C:
            grade, color = 'C', 'yellow'
        elif mi >= HTMLDashboardRenderer.MI_D:
            grade, color = 'D', 'orange'
        else:
            grade, color = 'F', 'red'
        # Show grade first to match tests (e.g., "A (85)")
        return (f'{grade} ({round(mi)})', color)

    def _status_complexity(self, value: object) -> tuple[str, str]:
        if not value or not isinstance(value, tuple) or value[0] is None:
            return ('unknown', 'gray')
        avg = float(value[0])
        grade, color = self._complexity_grade_color(avg)
        # Show grade first to match tests (e.g., "A (3.0)")
        return (f'{grade} ({avg:.1f})', color)

    def _status_codecov(self, value: object, branch: str) -> tuple[str, str]:
        # Master/develop: use provided value (env), do not fetch
        if branch in {'master', 'develop'}:
            if not value:
                return ('unknown', 'gray')
            try:
                p = round(float(str(value).strip().rstrip('%')))
            except Exception:
                return ('unknown', 'gray')
            color = self._color_for_percent(float(p))
            return (f'{p}%', color)

        # Feature: prefer live badge, fall back to provided value
        branch_for_badge = self.feature
        p = self._codecov_percent(branch_for_badge)
        if p is None and value:
            try:
                p = round(float(str(value).strip().rstrip('%')))
            except Exception:
                p = None
        if p is None:
            return ('unknown', 'gray')
        color = self._color_for_percent(float(p))
        return (f'{p}%', color)

    def _status_codefactor(self, value: object, branch: str) -> tuple[str, str]:
        if branch == 'master':
            branch_for_badge = None
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

    def _status_workflow(
        self, m: GithubWorkflowMetric, value: object, branch: str
    ) -> tuple[str, str]:
        if branch == 'master':
            branch_for_badge = None
        elif branch == 'feature':
            branch_for_badge = self.feature
        else:
            branch_for_badge = self.develop_branch
        status = self._github_badge_status(m.workflow_filename, branch_for_badge)
        if status is None:
            status = str(value or '').strip().lower()
        if status in {'success', 'succeeded', 'pass', 'passed', 'passing', 'ok'}:
            return ('passed', 'green')
        if status in {'fail', 'failed', 'failing', 'error', 'cancelled'}:
            return ('failed', 'red')
        if status in {'-', '', 'unknown', 'no status', 'no status yet'}:
            return ('unknown', 'gray')
        return (status, 'gray')

    @staticmethod
    def _fmt_int(v: object) -> str | None:
        if v in {None, ''}:
            return None
        try:
            return f'{int(str(v).replace(",", "").strip()):,}'
        except Exception:
            return None

    def _status_count(self, value: object) -> tuple[str, str]:
        formatted = self._fmt_int(value)
        if formatted is None:
            return ('-', 'gray')
        return (formatted, 'blue')

    def _status_loc(self, value: object) -> tuple[str, str]:
        tup = value if isinstance(value, tuple) else None
        if not tup:
            return ('-', 'gray')
        sloc, lloc = tup
        s = self._fmt_int(sloc) or '-'
        lloc_str = self._fmt_int(lloc) or '-'
        ratio: float | None = None
        try:
            raw_lloc = int(str(lloc).replace(',', '').strip()) if lloc is not None else 0
            if raw_lloc > 0:
                ratio = float(sloc) / float(raw_lloc)
        except Exception:
            ratio = None
        if ratio is None:
            return (f'{s}/{lloc_str}', 'gray')
        if ratio <= HTMLDashboardRenderer.RATIO_GREEN:
            color = 'green'
        elif ratio <= HTMLDashboardRenderer.RATIO_YELLOW_GREEN:
            color = 'yellow-green'
        elif ratio <= HTMLDashboardRenderer.RATIO_YELLOW:
            color = 'yellow'
        elif ratio <= HTMLDashboardRenderer.RATIO_ORANGE:
            color = 'orange'
        else:
            color = 'red'
        return (f'{ratio:.2f} ({s}/{lloc_str})', color)

    def _status_text_for_metric(self, key: str, branch: str) -> tuple[str, str] | None:
        """Return status and color for a metric/branch."""
        m = self.metric_by_key.get(key)
        if not m:
            return None
        attr = (
            'master'
            if branch == 'master'
            else ('develop' if branch == 'develop' else 'feature_value')
        )
        value = getattr(m, attr, None)

        result: tuple[str, str]
        if isinstance(m, DocstringCoverageMetric):
            result = self._status_docstring(value)
        elif isinstance(m, MaintainabilityMetric):
            result = self._status_maintainability(value)
        elif isinstance(m, ComplexityMetric):
            result = self._status_complexity(value)
        elif isinstance(m, CodecovMetric):
            result = self._status_codecov(value, branch)
        elif isinstance(m, CodeFactorMetric):
            result = self._status_codefactor(value, branch)
        elif isinstance(m, GithubWorkflowMetric):
            result = self._status_workflow(m, value, branch)
        elif isinstance(m, (FileCountMetric, FunctionCountMetric)):
            result = self._status_count(value)
        elif isinstance(m, LinesOfCodeMetric):
            result = self._status_loc(value)
        else:
            result = ('unknown', 'gray')
        return result

    def _value_item_html(self, key: str, branch: str, branch_label: str) -> str:
        """Render a single metric row with left label and right value.

        Returns:
            str: HTML for a row with two spans: a left-aligned branch
            label and a right-aligned colored value.
        """
        status = self._status_text_for_metric(key, branch)
        # Prepend a neutral icon per branch type
        icon_cls = (
            'fas fa-crown'
            if branch == 'master'
            else ('fas fa-hammer' if branch == 'develop' else 'fas fa-code-branch')
        )
        if status is not None:
            text, color = status
            return (
                '<div class="row">'
                f'<span class="item-label {color}">'
                f'<i class="{icon_cls} icon"></i>'
                f'{branch_label}</span>'
                f'<span class="item-value {color}">{text}</span>'
                '</div>'
            )
        return (
            '<div class="row">'
            f'<span class="item-label gray">'
            f'<i class="{icon_cls} icon"></i>'
            f'{branch_label}</span>'
            '<span class="item-value gray">unknown</span>'
            '</div>'
        )

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
            f'  <div class="card-title"><i class="{icon_class}"></i>{title}</div>\n'
            f'  <div class="values">\n{values_html}\n  </div>\n'
            f'</div>'
        )

    @staticmethod
    def render() -> str:
        """Return the rendered HTML string for the dashboard."""
        return ''


class HTMLDashboardRendererWithSpec(HTMLDashboardRenderer):
    """Renderer variant that uses an explicit card order spec."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        metrics: list[BaseMetric],
        feature: str,
        badge_gen: BadgeGenerator,
        cards_spec: list[tuple[str, str, str]],
        default_branch: str = 'master',
        develop_branch: str = 'develop',
    ) -> None:
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
        cards: list[str] = []
        for key, title, icon in self.cards_spec:
            m = self.metric_by_key.get(key)
            if not m:
                continue
            cards.append(self._card_html(title or m.label, icon, key))

        cards_html = '\n'.join(cards)

        return f"""<!DOCTYPE html>
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
