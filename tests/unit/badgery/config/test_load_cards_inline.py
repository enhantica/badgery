from __future__ import annotations

from pathlib import Path

from badgery.badges import BadgeGenerator
from badgery.config import build_metrics_from_config
from badgery.config import load_cards_from_yaml


def write_yaml(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def test_load_cards_from_yaml_supports_inline_mapping_and_booleans(tmp_path: Path):
    yml = tmp_path / '.badgery.yaml'
    write_yaml(
        yml,
        (
            'cards:\n'
            "  - group: 'Tests'\n"
            '    type: gh_action\n'
            '    title: Test code\n'
            '    workflow: ci.yaml\n'
            '    enabled: true\n'
            '  - group: Code Quality\n'
            '    type: radon_mi\n'
            '    title: MI\n'
            '    report: reports/{branch}/mi.json\n'
            '    enabled: false\n'
        ),
    )
    cards = load_cards_from_yaml(str(yml))
    assert isinstance(cards, list)
    assert cards[0]['group'] == 'Tests'
    assert cards[0]['enabled'] is True
    assert cards[1]['enabled'] is False

    # Disabled radon_mi should be skipped
    metrics, spec = build_metrics_from_config(cards, BadgeGenerator('org/repo'), feature='x')
    keys = {m.key for m in metrics}
    assert 'maintainability' not in keys
    # gh_action present
    assert any(s[0] == 'ci' for s in spec)

