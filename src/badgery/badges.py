# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Helpers for constructing external service URLs for badges/links."""

from __future__ import annotations

import os

REPO_DEFAULT = os.environ.get('GITHUB_REPOSITORY', 'easyscience/diffraction-lib')


class BadgeGenerator:
    """Minimal link container and helpers for service URLs."""

    def __init__(self, repo: str = REPO_DEFAULT, shields: str = '') -> None:
        """Initialize with GitHub `repo` and optional shields host."""
        self.repo = repo
        self.shields = shields
        self.github_workflows = f'https://github.com/{self.repo}/actions/workflows'
        self.codefactor = f'https://www.codefactor.io/repository/github/{self.repo}'
        self.codecov = f'https://codecov.io/gh/{self.repo}'

    def _badge(
        self,
        _section: str,
        _branch: str,
        _extra_params: dict[str, str] | None = None,
    ) -> str:
        """Return a placeholder badge URL.

        Returns:
            str: Empty string for now.
        """
        return ''

    def codecov_badge(self, _branch: str = 'master') -> str:
        """Return a Codecov badge URL.

        Returns:
            str: URL string (unused by renderer).
        """
        return ''

    def codefactor_badge(self, _branch: str = 'master') -> str:
        """Return a CodeFactor badge URL.

        Returns:
            str: URL string (unused by renderer).
        """
        return ''

    def github_workflow_badge_img(
        self,
        workflow: str,
        branch: str | None = None,
    ) -> str:
        """Return image URL for a workflow badge.

        Returns:
            str: URL string.
        """
        base = f'https://github.com/{self.repo}/actions/workflows/{workflow}/badge.svg'
        if branch and branch not in ('', 'master'):
            return f'{base}?branch={branch}'
        return base

    def github_workflow_badge_link(self, workflow: str) -> str:
        """Return the workflow runs page URL.

        Returns:
            str: URL string.
        """
        return f'https://github.com/{self.repo}/actions/workflows/{workflow}'

    def codecov_badge_img(self, branch: str | None = None) -> str:
        """Return image URL for a Codecov badge.

        Returns:
            str: URL string.
        """
        token = os.environ.get('CODECOV_TOKEN', 'qtsB5Q5BXO')
        repo = os.environ.get('CODECOV_REPO', self.repo)
        if branch and branch not in ('', 'master'):
            return f'https://codecov.io/gh/{repo}/branch/{branch}/graph/badge.svg?token={token}'
        return f'https://codecov.io/gh/{repo}/graph/badge.svg?token={token}'

    def codecov_badge_link(self) -> str:
        """Return Codecov dashboard URL for the repository.

        Returns:
            str: URL string.
        """
        repo = os.environ.get('CODECOV_REPO', self.repo)
        return f'https://codecov.io/gh/{repo}'

    def codefactor_badge_img(self, branch: str) -> str:
        """Return image URL for a CodeFactor grade badge.

        Returns:
            str: URL string.
        """
        return f'https://www.codefactor.io/repository/github/{self.repo}/badge/{branch}'

    def codefactor_badge_link(self, branch: str) -> str:
        """Return CodeFactor project overview URL for a branch.

        Returns:
            str: URL string.
        """
        return f'https://www.codefactor.io/repository/github/{self.repo}/overview/{branch}'
