from __future__ import annotations

import os

from badgery.badges import BadgeGenerator


def test_badge_generator_github_workflow_badge_img_master_branch():
    bg = BadgeGenerator(repo='org/repo')
    url = bg.github_workflow_badge_img('ci.yml', None)
    assert (
        url
        == 'https://github.com/org/repo/actions/workflows/ci.yml/badge.svg'
    )


def test_badge_generator_github_workflow_badge_img_specific_branch():
    bg = BadgeGenerator(repo='org/repo')
    url = bg.github_workflow_badge_img('ci.yml', 'feature-x')
    assert url == (
        'https://github.com/org/repo/actions/workflows/ci.yml/badge.svg'
        '?branch=feature-x'
    )


def test_badge_generator_links_codecov_and_codefactor(monkeypatch):
    monkeypatch.setenv('CODECOV_REPO', 'acme/radar')
    bg = BadgeGenerator(repo='org/repo')
    # Codecov link respects CODECOV_REPO
    assert bg.codecov_badge_link() == 'https://codecov.io/gh/acme/radar'

    # Codecov badge image for branch
    token = os.environ.get('CODECOV_TOKEN', 'qtsB5Q5BXO')
    u = bg.codecov_badge_img('dev')
    assert u == (
        f'https://codecov.io/gh/acme/radar/branch/dev/graph/badge.svg?token={token}'
    )

    # CodeFactor link and badge
    assert (
        bg.codefactor_badge_img('main')
        == 'https://www.codefactor.io/repository/github/org/repo/badge/main'
    )
    assert (
        bg.codefactor_badge_link('main')
        == 'https://www.codefactor.io/repository/github/org/repo/overview/main'
    )
