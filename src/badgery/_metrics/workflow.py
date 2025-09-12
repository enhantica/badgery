# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""GitHub workflow status metric."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from badgery.metrics import BaseMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


class GithubWorkflowMetric(BaseMetric):
    """Display GitHub Actions workflow status per branch."""

    def __init__(
        self,
        badge_gen: BadgeGenerator,
        workflow_filename: str,
        label: str,
        feature: str | None = None,
    ) -> None:
        """Initialize workflow metric with file name and label."""
        base = Path(workflow_filename).stem.replace('.', '-').replace('_', '-')
        key = base
        super().__init__(badge_gen, key=key, label=label, feature=feature)
        self.workflow_filename = workflow_filename

    @staticmethod
    def _env_key(base: str, branch: str) -> str:
        """Return the env var key for a workflow status."""
        return f'CI_WORKFLOW_{base.upper().replace("-", "_")}_{branch.upper()}'

    def read_all(self, _args: object) -> None:
        """Populate workflow status env vars for three branches."""
        base = self.key
        self.master = os.environ.get(self._env_key(base, 'master'), '')
        self.develop = os.environ.get(self._env_key(base, 'develop'), '')
        self.feature_value = os.environ.get(self._env_key(base, 'feature'), '')

    def badge(self, value: object) -> str:
        """Return a badge string (unused)."""
        return self.badge_gen.github_badge(self.workflow_filename, value)

    def refs(self) -> dict[str, str]:
        """Return workflow badge URLs for branches."""
        return {
            'master': self.badge('master'),
            'master_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
            'develop': self.badge('develop'),
            'develop_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
            'feature': self.badge(self.feature),
            'feature_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
        }
