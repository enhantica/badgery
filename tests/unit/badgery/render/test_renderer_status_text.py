from __future__ import annotations

import pytest

from badgery.badges import BadgeGenerator
from badgery.metrics import CodecovMetric
from badgery.metrics import CodeFactorMetric
from badgery.metrics import GithubWorkflowMetric
from badgery.render import HTMLDashboardRenderer


def test_grade_color_for_letter_and_unknown():
    r = HTMLDashboardRenderer([], feature='f', badge_gen=BadgeGenerator('r/x'))
    assert r._grade_color_for_letter('A') == 'green'
    assert r._grade_color_for_letter('b') == 'yellow-green'
    assert r._grade_color_for_letter('C') == 'yellow'
    assert r._grade_color_for_letter('D') == 'orange'
    assert r._grade_color_for_letter('E') == 'red'
    assert r._grade_color_for_letter('F') == 'red'
    assert r._grade_color_for_letter('') == 'gray'


def test_status_text_for_codecov_with_fetch_and_env(monkeypatch: pytest.MonkeyPatch):
    bg = BadgeGenerator('org/repo')
    cc = CodecovMetric(bg, feature='feat')
    # Provide env for master/develop
    monkeypatch.setenv('CI_CODECOV_MASTER', '91%')
    monkeypatch.setenv('CI_CODECOV_DEVELOP', '74%')
    monkeypatch.setenv('CI_CODECOV_FEATURE', '66%')
    cc.read_all(object())
    r = HTMLDashboardRenderer([cc], feature='feat', badge_gen=bg)

    # Force fetch to return a deterministically parsed percent for feature
    monkeypatch.setenv('CODECOV_REPO', 'org/repo')

    def fake_fetch(url: str, timeout: float = 8.0) -> str:  # noqa: ARG001
        if 'codecov' in url:
            return '<svg><text>83%</text></svg>'
        return ''

    monkeypatch.setattr(r, '_fetch', fake_fetch)

    # Master/develop use envs directly
    assert r._status_text_for_metric('codecov', 'master') == ('91%', 'green')
    assert r._status_text_for_metric('codecov', 'develop') == ('74%', 'yellow')
    # Feature prefers fetched percent; falls back to env if missing
    assert r._status_text_for_metric('codecov', 'feature') == ('83%', 'yellow-green')


def test_status_text_for_codefactor_with_fetch_and_env(monkeypatch: pytest.MonkeyPatch):
    bg = BadgeGenerator('org/repo')
    cf = CodeFactorMetric(bg, feature='feature-x')
    cf.read_all(object())
    r = HTMLDashboardRenderer([cf], feature='feature-x', badge_gen=bg, default_branch='main')

    # Simulate badge fetch producing a letter for master/develop/feature
    def fake_fetch(url: str, timeout: float = 8.0) -> str:  # noqa: ARG001
        if 'badge' in url:
            if 'overview/feature-x' in url or 'badge/feature-x' in url:
                return '<svg><text>B</text></svg>'
            if 'badge.svg' in url and 'actions' in url:
                return '<svg><text>passing</text></svg>'
        return ''

    monkeypatch.setattr(r, '_fetch', lambda *_args, **_kw: '')  # Disable external fetch paths
    # Without fetch, falls back to env. Set env for develop only.
    monkeypatch.setenv('CI_CODEFACTOR_DEVELOP', 'C')
    cf.read_all(object())

    # Master: fetch None -> value empty -> unknown gray
    assert r._status_text_for_metric('codefactor', 'master') == ('unknown', 'gray')
    # Develop: env 'C' -> yellow
    assert r._status_text_for_metric('codefactor', 'develop') == ('C', 'yellow')
    # Feature: env empty -> unknown gray
    assert r._status_text_for_metric('codefactor', 'feature') == ('unknown', 'gray')


def test_status_text_for_github_workflow(monkeypatch: pytest.MonkeyPatch):
    bg = BadgeGenerator('org/repo')
    gw = GithubWorkflowMetric(bg, workflow_filename='ci.yml', label='CI', feature='my-feature')
    gw.read_all(object())
    r = HTMLDashboardRenderer([gw], feature='my-feature', badge_gen=bg, develop_branch='develop')

    # First case: fetch returns statuses
    def fake_fetch(url: str, timeout: float = 8.0) -> str:  # noqa: ARG001
        if 'badge.svg' in url and 'actions' in url:
            if 'branch=my-feature' in url:
                return '<svg><text>failing</text></svg>'
            if 'ci.yml' in url and 'branch=' not in url:
                return '<svg><text>passing</text></svg>'
        return ''

    monkeypatch.setattr(r, '_fetch', fake_fetch)

    assert r._status_text_for_metric(gw.key, 'master') == ('passed', 'green')
    assert r._status_text_for_metric(gw.key, 'feature') == ('failed', 'red')

    # Fallback to env when fetch returns nothing
    monkeypatch.setattr(r, '_fetch', lambda *_a, **_k: '')
    monkeypatch.setenv('CI_WORKFLOW_CI_DEVELOP', 'queued')
    gw.read_all(object())
    assert r._status_text_for_metric(gw.key, 'develop') == ('queued', 'gray')
