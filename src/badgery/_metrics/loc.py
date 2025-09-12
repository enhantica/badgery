# SPDX-FileCopyrightText: 2025 Badgery contributors <https://github.com/enhantica/badgery>
# SPDX-License-Identifier: MIT
"""Source and logical lines of code (Radon raw JSON)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from badgery.metrics import BaseMetric

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


class LinesOfCodeMetric(BaseMetric):
    """Aggregate SLOC and LLOC from Radon raw metrics report."""

    key = 'loc'
    label = 'Source/Logical lines of code'

    def __init__(self, badge_gen: BadgeGenerator, feature: str | None = None) -> None:
        """Initialize line count metric."""
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _extract_sloc_lloc(obj: object) -> tuple[int, int]:
        sloc = 0
        lloc = 0
        if isinstance(obj, dict):
            if 'sloc' in obj or 'lloc' in obj:
                try:
                    sloc += int(obj.get('sloc', 0))
                    lloc += int(obj.get('lloc', 0))
                except Exception as exc:
                    logging.debug('raw sloc/lloc parse error: %s', exc)
            raw = obj.get('raw') if isinstance(obj.get('raw'), dict) else None
            if raw:
                try:
                    sloc += int(raw.get('sloc', 0))
                    lloc += int(raw.get('lloc', 0))
                except Exception as exc:
                    logging.debug('raw.raw sloc/lloc parse error: %s', exc)
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    s, lloc_part = LinesOfCodeMetric._extract_sloc_lloc(v)
                    sloc += s
                    lloc += lloc_part
        elif isinstance(obj, list):
            for it in obj:
                s, lloc_part = LinesOfCodeMetric._extract_sloc_lloc(it)
                sloc += s
                lloc += lloc_part
        return (sloc, lloc)

    @staticmethod
    def _sum_raw_metrics(path: str | None) -> tuple[int, int] | None:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        return LinesOfCodeMetric._extract_sloc_lloc(data)

    def read_all(self, args: object) -> None:
        """Populate SLOC/LLOC tuples for three branches."""
        self.master = self._sum_raw_metrics(getattr(args, 'raw_metrics_master', None))
        self.develop = self._sum_raw_metrics(getattr(args, 'raw_metrics_develop', None))
        self.feature_value = self._sum_raw_metrics(getattr(args, 'raw_metrics_feature', None))
