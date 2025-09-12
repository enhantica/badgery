from __future__ import annotations

from pathlib import Path

from badgery.badges import BadgeGenerator
from badgery.config import build_metrics_from_config
from badgery.config import group_icon
from badgery.config import load_settings_from_yaml


def write_yaml(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def test_load_settings_and_cards_with_branch_placeholders(tmp_path: Path):
    yml = tmp_path / '.badgery.yaml'
    write_yaml(
        yml,
        """
default_branch: main
develop_branch: develop

cards:
  - group: Code Quality
    type: radon_mi
    title: Maintainability index with radon
    report: reports/{branch}/maintainability-index.json
    enabled: true

  - group: Tests
    type: gh_action
    title: Test code and package
    workflow: code.yaml
    enabled: true
        """.strip(),
    )

    settings = load_settings_from_yaml(str(yml))
    assert settings['default_branch'] == 'main'
    assert settings['develop_branch'] == 'develop'
    assert isinstance(settings['cards'], list)
    assert settings['cards'][0]['group'] == 'Code Quality'
    assert settings['cards'][1]['workflow'] == 'code.yaml'


def test_group_icon_mapping_basic():
    assert group_icon('Tests') == 'fas fa-vial'
    assert group_icon('Code Quality') == 'fas fa-gauge'
    assert group_icon('Coverage') == 'fas fa-square-poll-vertical'
    # Fallbacks
    assert group_icon('Security') == 'fas fa-lock'
    assert group_icon('Publish to PyPI') == 'fas fa-box'


def test_build_metrics_from_config_constructs_metrics():
    cards = [
        {
            'group': 'Code Quality',
            'type': 'radon_mi',
            'title': 'MI',
            'report': 'reports/{branch}/maintainability-index.json',
            'enabled': True,
        },
        {
            'group': 'Tests',
            'type': 'gh_action',
            'title': 'CI',
            'workflow': 'ci.yml',
            'enabled': True,
        },
    ]
    bg = BadgeGenerator(repo='acme/proj')
    metrics, spec = build_metrics_from_config(cards, bg, feature='feature-x')
    keys = {m.key for m in metrics}
    assert 'maintainability' in keys
    # Workflow metric key derived from workflow filename
    assert any(k[0] == 'ci' and k[1] == 'CI' for k in spec)
