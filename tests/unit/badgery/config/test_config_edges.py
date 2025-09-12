from __future__ import annotations

from pathlib import Path

from badgery.badges import BadgeGenerator
from badgery.config import build_metrics_from_config
from badgery.config import group_icon
from badgery.config import load_cards_from_yaml
from badgery.config import load_settings_from_yaml


def test_loaders_missing_file_defaults(tmp_path: Path):
    missing = tmp_path / 'nope.yaml'
    assert load_cards_from_yaml(str(missing)) == []
    s = load_settings_from_yaml(str(missing))
    assert s['default_branch'] == 'master'
    assert s['develop_branch'] == 'develop'
    assert s['cards'] == []


def test_load_settings_top_level_parsing_with_quotes(tmp_path: Path):
    yml = tmp_path / '.badgery.yaml'
    yml.write_text(
        (
            "default_branch: 'main'\n"
            'develop_branch: "develop"\n'
            'some_other: ignored\n'
            '\n'
            'cards:\n'
            '  - group: Build & Release\n'
            '    type: unknown\n'
        ),
        encoding='utf-8',
    )
    s = load_settings_from_yaml(str(yml))
    assert s['default_branch'] == 'main'
    assert s['develop_branch'] == 'develop'


def test_build_metrics_skips_unknown_and_missing_workflow(tmp_path: Path):
    cards = [
        {'group': 'X', 'type': 'unknown', 'title': 'U'},  # unknown type
        {'group': 'Build & Release', 'type': 'gh_action', 'title': 'Build'},  # no workflow
        {'group': 'Size', 'type': 'radon_files', 'title': 'Files'},
        {'group': 'Size', 'type': 'radon_funcs', 'title': 'Funcs'},
    ]
    bg = BadgeGenerator('org/repo')
    metrics, spec = build_metrics_from_config(cards, bg, feature='f')
    keys = {m.key for m in metrics}
    # unknown and gh_action without workflow are skipped
    assert 'files' in keys and 'funcs' in keys
    assert all(k[0] in ('files', 'funcs') for k in spec)


def test_group_icon_additional_mappings():
    assert group_icon('Build & Release') == 'fas fa-rocket'
    assert group_icon('Size') == 'fas fa-file-code'
    # fuzzy matching and precedence
    assert group_icon('publish release to pypi') == 'fas fa-rocket'
