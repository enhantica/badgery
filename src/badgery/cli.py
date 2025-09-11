"""CLI for generating the Badgery HTML dashboard."""

from __future__ import annotations

import argparse
import logging
import os
from glob import glob
from pathlib import Path
from typing import Optional

from badgery.badges import BadgeGenerator
from badgery.config import build_metrics_from_config
from badgery.config import load_settings_from_yaml
from badgery.render import HTMLDashboardRendererWithSpec


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
    complexity_pattern = None
    maintainability_pattern = None
    raw_pattern = None
    docstring_pattern = None

    for card in cards:
        if not card.get('enabled', True):
            continue
        ctype = str(card.get('type', '')).strip().lower()
        if ctype in {'radon_cc', 'radon_files', 'radon_funcs'}:
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
        if '{branch}' in pattern:
            candidate = pattern.replace('{branch}', branch)
        else:
            candidate = pattern.replace('**', branch)
        p = Path(candidate)
        if p.exists():
            return str(p)
        matches = glob(candidate)
        if matches:
            return matches[0]
        return None

    args.cyclomatic_complexity_master = _resolve(
        complexity_pattern, args.default_branch
    ) or os.environ.get('CI_COMPLEXITY_MASTER')
    args.cyclomatic_complexity_develop = _resolve(
        complexity_pattern, args.develop_branch
    ) or os.environ.get('CI_COMPLEXITY_DEVELOP')
    args.cyclomatic_complexity_feature = _resolve(
        complexity_pattern, feature_branch
    ) or os.environ.get('CI_COMPLEXITY_FEATURE')

    args.maintainability_index_master = _resolve(
        maintainability_pattern, args.default_branch
    ) or os.environ.get('CI_MAINTAINABILITY_MASTER')
    args.maintainability_index_develop = _resolve(
        maintainability_pattern, args.develop_branch
    ) or os.environ.get('CI_MAINTAINABILITY_DEVELOP')
    args.maintainability_index_feature = _resolve(
        maintainability_pattern, feature_branch
    ) or os.environ.get('CI_MAINTAINABILITY_FEATURE')

    args.raw_metrics_master = _resolve(raw_pattern, args.default_branch) or os.environ.get(
        'CI_RAW_METRICS_MASTER'
    )
    args.raw_metrics_develop = _resolve(raw_pattern, args.develop_branch) or os.environ.get(
        'CI_RAW_METRICS_DEVELOP'
    )
    args.raw_metrics_feature = _resolve(raw_pattern, feature_branch) or os.environ.get(
        'CI_RAW_METRICS_FEATURE'
    )

    args.coverage_docstring_master = _resolve(
        docstring_pattern, args.default_branch
    ) or os.environ.get('CI_DOCSTRING_MASTER')
    args.coverage_docstring_develop = _resolve(
        docstring_pattern, args.develop_branch
    ) or os.environ.get('CI_DOCSTRING_DEVELOP')
    args.coverage_docstring_feature = _resolve(
        docstring_pattern, feature_branch
    ) or os.environ.get('CI_DOCSTRING_FEATURE')

    return args


def main() -> None:
    """Run the dashboard generation from CLI arguments."""
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))

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
