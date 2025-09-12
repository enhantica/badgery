from __future__ import annotations

import json
from pathlib import Path

from badgery.badges import BadgeGenerator
from badgery.metrics import LinesOfCodeMetric


def test_loc_nested_raw_fields_and_invalid_values(tmp_path: Path):
    # Nested dictionaries with raw and direct sloc/lloc and some invalid values
    data = {
        "pkg": {
            "module": {
                "file1": {"raw": {"sloc": 10, "lloc": 5}},
                "file2": {"sloc": 3, "lloc": 2},
                "file3": {"raw": {"sloc": "bad", "lloc": 7}},  # invalid sloc ignored
            },
            "list": [
                {"raw": {"sloc": 4, "lloc": 4}},
                {"sloc": 1, "lloc": 1},
            ],
        }
    }
    p = tmp_path / 'raw.json'
    p.write_text(json.dumps(data), encoding='utf-8')

    m = LinesOfCodeMetric(BadgeGenerator('x/y'), feature='f')
    args = type(
        'Args',
        (),
        {
            'raw_metrics_master': str(p),
            'raw_metrics_develop': str(p),
            'raw_metrics_feature': str(p),
        },
    )
    m.read_all(args)
    # Current implementation adds values both at node and again when recursing into 'raw'
    # file1: raw counted twice (10,5) x2 -> (20,10)
    # file2: (3,2)
    # file3: invalid sloc prevents both sloc/lloc addition (0,0)
    # list item1: raw counted twice (4,4) x2 -> (8,8)
    # list item2: (1,1)
    # Total: (32, 21)
    assert m.master == (32, 21)
    assert m.develop == (32, 21)
    assert m.feature_value == (32, 21)
