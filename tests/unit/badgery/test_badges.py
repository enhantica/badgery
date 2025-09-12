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


def test_github_workflow_badge_link():
    bg = BadgeGenerator(repo='org/repo')
    assert (
        bg.github_workflow_badge_link('ci.yml')
        == 'https://github.com/org/repo/actions/workflows/ci.yml'
    )


def test_codecov_badge_img_default_and_master(monkeypatch):
    monkeypatch.setenv('CODECOV_REPO', 'org/repo')
    token = os.environ.get('CODECOV_TOKEN', 'qtsB5Q5BXO')
    bg = BadgeGenerator(repo='org/repo')
    # Default (no branch) uses repository graph URL
    assert bg.codecov_badge_img(None) == f'https://codecov.io/gh/org/repo/graph/badge.svg?token={token}'
    # Master also uses repository graph URL (no branch path)
    assert bg.codecov_badge_img('master') == f'https://codecov.io/gh/org/repo/graph/badge.svg?token={token}'


def test_private_badge_helpers_return_empty_strings():
    bg = BadgeGenerator('org/repo')
    # The current implementation does not use these helpers; ensure they return empty strings
    assert bg._badge('section', 'branch') == ''
    assert bg.codecov_badge('dev') == ''
    assert bg.codefactor_badge('dev') == ''
