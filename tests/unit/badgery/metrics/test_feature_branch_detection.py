from __future__ import annotations

from badgery.badges import BadgeGenerator
from badgery.metrics import ComplexityMetric


def test_detect_feature_branch_from_env_ci_branch(monkeypatch):
    monkeypatch.delenv('GITHUB_REF_NAME', raising=False)
    monkeypatch.delenv('GITHUB_HEAD_REF', raising=False)
    monkeypatch.setenv('CI_BRANCH', 'feat-ci')
    m = ComplexityMetric(BadgeGenerator('x/y'), feature=None)
    assert m.feature == 'feat-ci'


def test_detect_feature_branch_from_env_ref_name(monkeypatch):
    monkeypatch.delenv('CI_BRANCH', raising=False)
    monkeypatch.delenv('GITHUB_HEAD_REF', raising=False)
    monkeypatch.setenv('GITHUB_REF_NAME', 'feat-ref')
    m = ComplexityMetric(BadgeGenerator('x/y'), feature=None)
    assert m.feature == 'feat-ref'


def test_detect_feature_branch_from_env_head_ref(monkeypatch):
    monkeypatch.delenv('CI_BRANCH', raising=False)
    monkeypatch.delenv('GITHUB_REF_NAME', raising=False)
    monkeypatch.setenv('GITHUB_HEAD_REF', 'feat-head')
    m = ComplexityMetric(BadgeGenerator('x/y'), feature=None)
    assert m.feature == 'feat-head'


def test_detect_feature_branch_unknown(monkeypatch):
    monkeypatch.delenv('CI_BRANCH', raising=False)
    monkeypatch.delenv('GITHUB_REF_NAME', raising=False)
    monkeypatch.delenv('GITHUB_HEAD_REF', raising=False)
    m = ComplexityMetric(BadgeGenerator('x/y'), feature=None)
    assert m.feature == 'unknown'
