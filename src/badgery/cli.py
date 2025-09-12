# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""CLI for generating the Badgery HTML dashboard."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from badgery.badges import BadgeGenerator
from badgery.config import build_metrics_from_config
from badgery.config import load_settings_from_yaml
from badgery.render import HTMLDashboardRendererWithSpec

# Placeholder token used in report path patterns
BRANCH_TOKEN = '{' + 'branch' + '}'


def _collect_report_patterns(
    cards: list[dict],
) -> tuple[str | None, str | None, str | None, str | None]:
    """Return patterns for complexity, MI, raw, and docstring reports.

    The function inspects enabled cards and extracts the first matching
    pattern per metric type.
    """
    complexity_pattern = None
    maintainability_pattern = None
    raw_pattern = None
    docstring_pattern = None
    for card in cards:
        if not card.get('enabled', True):
            continue
        ctype = str(card.get('type', '')).strip().lower()
        if ctype in {'radon_cc', 'radon_files', 'radon_funcs', 'radon_funcs_per_file', 'radon_ff'}:
            complexity_pattern = card.get('report') or card.get('dir') or complexity_pattern
        elif ctype == 'radon_mi':
            maintainability_pattern = card.get('report') or maintainability_pattern
        elif ctype == 'radon_loc':
            raw_pattern = card.get('report') or raw_pattern
        elif ctype == 'interrogate':
            docstring_pattern = card.get('report') or docstring_pattern
    return complexity_pattern, maintainability_pattern, raw_pattern, docstring_pattern


def _resolve_pattern(pattern: str | None, branch: str) -> str | None:
    if not pattern:
        return None
    if BRANCH_TOKEN in pattern:
        candidate = pattern.replace(BRANCH_TOKEN, branch)
    else:
        candidate = pattern.replace('**', branch)
    p = Path(candidate)
    if p.exists():
        return str(p)
    # Prefer pathlib over glob module (PTH207)
    parent = p.parent
    pattern = p.name
    if parent.exists():
        for match in parent.glob(pattern):
            return str(match)
    return None


def parse_args() -> argparse.Namespace:
    """Parse CLI args and enrich from config.

    Returns:
        argparse.Namespace: Args with paths resolved from the project
        `.badgery.yaml` (cards, branches, report paths).
    """
    parser = argparse.ArgumentParser(description='Generate an HTML dashboard of status badges.')
    parser.add_argument(
        '--output',
        default='BADGES.html',
        help='Output HTML file (default: BADGES.html)',
    )
    parser.add_argument(
        '--repo',
        required=True,
        help='GitHub repository, e.g. org/repo (required)',
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
    args = parser.parse_args()
    settings = load_settings_from_yaml(args.config)
    cards = settings.get('cards', [])
    args.cards_config = cards
    args.default_branch = str(settings.get('default_branch', 'master'))
    args.develop_branch = str(settings.get('develop_branch', 'develop'))

    feature_branch = args.branch
    (
        complexity_pattern,
        maintainability_pattern,
        raw_pattern,
        docstring_pattern,
    ) = _collect_report_patterns(cards)

    args.cyclomatic_complexity_master = _resolve_pattern(
        complexity_pattern,
        args.default_branch,
    ) or os.environ.get('CI_COMPLEXITY_MASTER')
    args.cyclomatic_complexity_develop = _resolve_pattern(
        complexity_pattern,
        args.develop_branch,
    ) or os.environ.get('CI_COMPLEXITY_DEVELOP')
    args.cyclomatic_complexity_feature = _resolve_pattern(
        complexity_pattern,
        feature_branch,
    ) or os.environ.get('CI_COMPLEXITY_FEATURE')

    args.maintainability_index_master = _resolve_pattern(
        maintainability_pattern,
        args.default_branch,
    ) or os.environ.get('CI_MAINTAINABILITY_MASTER')
    args.maintainability_index_develop = _resolve_pattern(
        maintainability_pattern,
        args.develop_branch,
    ) or os.environ.get('CI_MAINTAINABILITY_DEVELOP')
    args.maintainability_index_feature = _resolve_pattern(
        maintainability_pattern,
        feature_branch,
    ) or os.environ.get('CI_MAINTAINABILITY_FEATURE')

    args.raw_metrics_master = _resolve_pattern(raw_pattern, args.default_branch) or os.environ.get(
        'CI_RAW_METRICS_MASTER',
    )
    args.raw_metrics_develop = _resolve_pattern(
        raw_pattern,
        args.develop_branch,
    ) or os.environ.get('CI_RAW_METRICS_DEVELOP')
    args.raw_metrics_feature = _resolve_pattern(raw_pattern, feature_branch) or os.environ.get(
        'CI_RAW_METRICS_FEATURE',
    )

    args.coverage_docstring_master = _resolve_pattern(
        docstring_pattern,
        args.default_branch,
    ) or os.environ.get('CI_DOCSTRING_MASTER')
    args.coverage_docstring_develop = _resolve_pattern(
        docstring_pattern,
        args.develop_branch,
    ) or os.environ.get('CI_DOCSTRING_DEVELOP')
    args.coverage_docstring_feature = _resolve_pattern(
        docstring_pattern,
        feature_branch,
    ) or os.environ.get('CI_DOCSTRING_FEATURE')

    return args


def main() -> None:
    """Run the dashboard generation from CLI arguments."""
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    # Inform about config presence after logging is configured
    cfg_file = getattr(args, 'config', '.badgery.yaml')
    cfg_path = Path(cfg_file)
    if cfg_path.exists():
        logging.info(' Using config %s', cfg_file)

    feature = args.branch
    badge_gen = BadgeGenerator(repo=args.repo)
    metrics, cards_spec = build_metrics_from_config(args.cards_config, badge_gen, feature)

    for metric in metrics:
        try:
            metric.read_all(args)
        except Exception as exc:
            logging.debug('Metric read failed for %s: %s', getattr(metric, 'key', '?'), exc)

    renderer = HTMLDashboardRendererWithSpec(
        metrics,
        feature,
        badge_gen,
        cards_spec,
        default_branch=args.default_branch,
        develop_branch=args.develop_branch,
    )
    html = renderer.render()
    Path(args.output).write_text(html, encoding='utf-8')
