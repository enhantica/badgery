from __future__ import annotations

from pathlib import Path

from badgery.config import group_icon
from badgery.config import load_settings_from_yaml


def test_load_settings_without_cards_section(tmp_path: Path):
    yml = tmp_path / '.badgery.yaml'
    yml.write_text('default_branch: main\n# no cards here\n', encoding='utf-8')
    s = load_settings_from_yaml(str(yml))
    assert s['default_branch'] == 'main'
    assert s['develop_branch'] == 'develop'  # default preserved
    assert s['cards'] == []


def test_group_icon_default_fallback():
    assert group_icon('unknown-group') == 'fas fa-gauge'
