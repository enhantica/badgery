from __future__ import annotations

import os
from typing import Dict

REPO_DEFAULT = os.environ.get('GITHUB_REPOSITORY', 'easyscience/diffraction-lib')


class BadgeGenerator:
    """Minimal link container and helpers for service URLs."""

    def __init__(self, repo: str = REPO_DEFAULT, shields: str = '') -> None:
        self.repo = repo
        self.shields = shields
        self.github_workflows = f'https://github.com/{self.repo}/actions/workflows'
        self.codefactor = f'https://www.codefactor.io/repository/github/{self.repo}'
        self.codecov = f'https://codecov.io/gh/{self.repo}'

    def _badge(self, section: str, branch: str, extra_params: Dict[str, str] | None = None) -> str:
        return ''

    def codecov_badge(self, branch: str = 'master') -> str:
        return ''

    def codefactor_badge(self, branch: str = 'master') -> str:
        return ''

    def github_workflow_badge_img(self, workflow: str, branch: str | None = None) -> str:
        base = f'https://github.com/{self.repo}/actions/workflows/{workflow}/badge.svg'
        if branch and branch not in ('', 'master'):
            return f'{base}?branch={branch}'
        return base

    def github_workflow_badge_link(self, workflow: str) -> str:
        return f'https://github.com/{self.repo}/actions/workflows/{workflow}'

    def codecov_badge_img(self, branch: str | None = None) -> str:
        token = os.environ.get('CODECOV_TOKEN', 'qtsB5Q5BXO')
        repo = os.environ.get('CODECOV_REPO', self.repo)
        if branch and branch not in ('', 'master'):
            return f'https://codecov.io/gh/{repo}/branch/{branch}/graph/badge.svg?token={token}'
        return f'https://codecov.io/gh/{repo}/graph/badge.svg?token={token}'

    def codecov_badge_link(self) -> str:
        repo = os.environ.get('CODECOV_REPO', self.repo)
        return f'https://codecov.io/gh/{repo}'

    def codefactor_badge_img(self, branch: str) -> str:
        return f'https://www.codefactor.io/repository/github/{self.repo}/badge/{branch}'

    def codefactor_badge_link(self, branch: str) -> str:
        return f'https://www.codefactor.io/repository/github/{self.repo}/overview/{branch}'
