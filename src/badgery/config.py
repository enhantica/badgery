# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Configuration loading and mapping utilities for Badgery."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Optional

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator
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


def _parse_scalar(val: str) -> Any:
    """Parse a YAML-like scalar: booleans and quoted strings.

    Returns:
        Any: Parsed Python value for the scalar string.

    Notes:
        This is a tiny helper to keep load functions simpler and reduce
        complexity without introducing a real YAML parser dependency.
    """
    sval = val.strip()
    low = sval.lower()
    if low in ('true', 'false'):
        return low == 'true'
    if (sval.startswith("'") and sval.endswith("'")) or (
        sval.startswith('"') and sval.endswith('"')
    ):
        return sval[1:-1]
    return sval


def _parse_inline_mapping(rest: str, current: dict[str, Any]) -> None:
    if rest and ':' in rest:
        key, val = rest.split(':', 1)
        current[key.strip()] = _parse_scalar(val)


def load_cards_from_yaml(path: str) -> list[dict[str, Any]]:
    """Load the `cards:` list from `.badgery.yaml`.

    Returns:
        list[dict[str, Any]]: Card mappings in declaration order.
    """
    p = Path(path)
    if not p.exists():
        logging.info('Config %s not found; using empty card list', path)
        return []
    lines = p.read_text(encoding='utf-8').splitlines()
    # Find the start of the cards section first to reduce branching
    start = None
    for idx, raw in enumerate(lines):
        s = raw.strip()
        if s and not s.startswith('#') and s == 'cards:':
            start = idx + 1
            break
    if start is None:
        return []

    items: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None
    current_indent = 0
    for raw in lines[start:]:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if line.lstrip().startswith('- '):
            current = {}
            items.append(current)
            current_indent = len(line) - len(line.lstrip())
            rest = line.lstrip()[2:].strip()
            _parse_inline_mapping(rest, current)
            continue
        if current is None:
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= current_indent or ':' not in line:
            continue
        key, val = line.strip().split(':', 1)
        current[key.strip()] = _parse_scalar(val)
    return items


def load_settings_from_yaml(path: str) -> dict[str, Any]:
    """Load top-level settings (default/develop) and cards.

    Returns:
        dict[str, Any]: Keys `default_branch`, `develop_branch`, and
        `cards` with parsed values.
    """
    p = Path(path)
    settings: dict[str, Any] = {
        'default_branch': 'master',
        'develop_branch': 'develop',
        'cards': [],
    }
    if not p.exists():
        logging.info('Config %s not found; using defaults and empty card list', path)
        return settings

    lines = p.read_text(encoding='utf-8').splitlines()
    # Parse top-level settings until 'cards:'
    in_cards = False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not in_cards:
            if line.strip() == 'cards:':
                in_cards = True
                break
            if ':' in line and not line.startswith(' '):
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip()
                if val.lower() in ('true', 'false'):
                    parsed = val.lower() == 'true'
                else:
                    if (val.startswith("'") and val.endswith("'")) or (
                        val.startswith('"') and val.endswith('"')
                    ):
                        parsed = val[1:-1]
                    else:
                        parsed = val
                if key in ('default_branch', 'develop_branch'):
                    settings[key] = parsed
        else:
            break

    # Parse cards list using existing helper
    settings['cards'] = load_cards_from_yaml(path)
    return settings


def group_icon(group: str) -> str:
    """Return a Font Awesome icon class for a group name."""
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


def build_metrics_from_config(  # noqa: C901 - acceptable complexity
    cards: list[dict[str, Any]],
    badge_gen: 'BadgeGenerator',
    feature: str,
):
    """Construct metric instances and an ordered card spec.

    Returns:
        tuple[list, list[tuple[str, str, str]]]: The metric objects
        and an ordered card specification.
    """
    metrics: list[BaseMetric] = []
    cards_spec: list[tuple[str, str, str]] = []

    singleton_by_type: dict[str, BaseMetric] = {}

    def _get_or_create(ctype: str) -> BaseMetric | None:
        if ctype in singleton_by_type:
            return singleton_by_type[ctype]
        mapping: dict[str, type[BaseMetric]] = {
            'codefactor': CodeFactorMetric,
            'codecov': CodecovMetric,
            'codecove': CodecovMetric,  # alias
            'radon_mi': MaintainabilityMetric,
            'radon_cc': ComplexityMetric,
            'radon_loc': LinesOfCodeMetric,
            'radon_files': FileCountMetric,
            'radon_funcs': FunctionCountMetric,
            'interrogate': DocstringCoverageMetric,
        }
        cls = mapping.get(ctype)
        if cls is None:
            return None
        inst: BaseMetric = cls(badge_gen, feature=feature)
        singleton_by_type[ctype] = inst
        return inst

    for card in cards:
        if not card.get('enabled', True):
            continue
        ctype = str(card.get('type', '')).strip().lower()
        title = card.get('title') or ''
        group = card.get('group') or ''
        icon = group_icon(group)

        if ctype == 'gh_action':
            workflow = card.get('workflow') or card.get('file')
            if not workflow:
                logging.debug('Skipping gh_action without workflow/file in card %s', card)
                continue
            metric = GithubWorkflowMetric(
                badge_gen,
                workflow_filename=str(workflow),
                label=title,
                feature=feature,
            )
            metrics.append(metric)
            key = Path(str(workflow)).stem.replace('.', '-').replace('_', '-')
            cards_spec.append((key, title, icon))
            continue

        metric = _get_or_create(ctype)
        if metric is None:
            logging.debug('Unknown card type %r; skipping', ctype)
            continue
        if title:
            metric.label = title
        if metric not in metrics:
            metrics.append(metric)
        cards_spec.append((metric.key, metric.label or title, icon))

    return metrics, cards_spec
