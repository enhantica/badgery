from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Optional
from typing import Tuple

if TYPE_CHECKING:
    from badgery.badges import BadgeGenerator


def _detect_feature_branch() -> str:
    return (
        os.environ.get('CI_BRANCH')
        or os.environ.get('GITHUB_REF_NAME')
        or os.environ.get('GITHUB_HEAD_REF')
        or 'unknown'
    )


class BaseMetric:
    key: str = ''
    label: str = ''
    thresholds: list = []
    reverse: bool = False
    badge_url_func: Any = None

    def __init__(
        self,
        badge_gen: 'BadgeGenerator',
        key=None,
        label=None,
        feature: str | None = None,
    ):
        self.badge_gen = badge_gen
        if key is not None:
            self.key = key
        if label is not None:
            self.label = label
        self.feature = feature or _detect_feature_branch()
        self.master = None
        self.develop = None
        self.feature_value = None

    def read_value(self, path: str):
        raise NotImplementedError

    def read_all(self, args):
        raise NotImplementedError

    def format_value(self, value):
        return str(value)

    def badge(self, value):
        raise NotImplementedError

    def refs(self):
        return {
            'master': self.badge(self.master),
            'master_url': '#',
            'develop': self.badge(self.develop),
            'develop_url': '#',
            'feature': self.badge(self.feature_value),
            'feature_url': '#',
        }


class MaintainabilityMetric(BaseMetric):
    key = 'maintainability'
    label = 'Maintainability index with radon'
    thresholds = [
        (85, 'A', 'brightgreen'),
        (70, 'B', 'green'),
        (50, 'C', 'yellow'),
        (30, 'D', 'orange'),
        (0, 'F', 'red'),
    ]
    reverse = False

    def __init__(self, badge_gen: BadgeGenerator, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_value(self, path: str):
        if path and Path(path).exists():
            try:
                data = json.loads(Path(path).read_text(encoding='utf-8'))
                mi_values = []
                for value in data.values():
                    if isinstance(value, dict):
                        mi = value.get('mi')
                        if isinstance(mi, (int, float)):
                            mi_values.append(mi)
                if mi_values:
                    avg_mi = sum(mi_values) / len(mi_values)
                    return (avg_mi, len(mi_values))
            except Exception as exc:
                logging.debug('Failed to read maintainability from %s: %s', path, exc)
        return (None, None)

    def read_all(self, args):
        self.master = self.read_value(args.maintainability_index_master)
        self.develop = self.read_value(args.maintainability_index_develop)
        self.feature_value = self.read_value(args.maintainability_index_feature)

    def format_value(self, value):
        if (
            not value
            or not isinstance(value, tuple)
            or value[0] is None
            or value[1] is None
            or value[1] == 0
        ):
            return 'unknown'
        mi, count = value
        mi_rounded = round(mi)
        return f'{mi_rounded} over {count} files'

    def badge(self, value):
        return ''


class ComplexityMetric(BaseMetric):
    key = 'complexity'
    label = 'Cyclomatic complexity with radon'
    thresholds = [
        (5, 'A', 'brightgreen'),
        (10, 'B', 'green'),
        (15, 'C', 'yellow'),
        (20, 'D', 'orange'),
    ]
    reverse = True

    def __init__(self, badge_gen: BadgeGenerator, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_value(self, path: str):
        if path and Path(path).exists():
            try:
                data = json.loads(Path(path).read_text(encoding='utf-8'))
                complexities = []
                for file_data in data.values():
                    if isinstance(file_data, list):
                        for item in file_data:
                            if isinstance(item, dict):
                                complexity_value = item.get('complexity')
                                if isinstance(complexity_value, (int, float)):
                                    complexities.append(complexity_value)
                if complexities:
                    avg_complexity = sum(complexities) / len(complexities)
                    return (avg_complexity, len(complexities))
            except Exception as exc:
                logging.debug('Failed to read complexity from %s: %s', path, exc)
        return (None, None)

    def read_all(self, args):
        self.master = self.read_value(args.cyclomatic_complexity_master)
        self.develop = self.read_value(args.cyclomatic_complexity_develop)
        self.feature_value = self.read_value(args.cyclomatic_complexity_feature)

    def format_value(self, value):
        if (
            not value
            or not isinstance(value, tuple)
            or value[0] is None
            or value[1] is None
            or value[1] == 0
        ):
            return 'unknown'
        avg, count = value
        return f'{avg:.1f} over {count} funcs'

    def badge(self, value):
        return ''


class DocstringCoverageMetric(BaseMetric):
    key = 'docstring'
    label = 'Docstring coverage with interrogate'
    thresholds = [
        (90, '', 'brightgreen'),
        (70, '', 'yellow'),
        (50, '', 'orange'),
        (0, '', 'red'),
    ]
    reverse = False

    def __init__(self, badge_gen: BadgeGenerator, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_value(self, path: str):
        if path and Path(path).exists():
            lines = Path(path).read_text(encoding='utf-8').splitlines()
            for line in lines:
                if line.startswith('| TOTAL'):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        percent = parts[-2].strip()
                        return percent
            for line in reversed(lines):
                if 'actual:' in line:
                    after_actual = line.split('actual:')[-1].strip()
                    percent = after_actual.split()[0]
                    return percent
        return ''

    def read_all(self, args):
        self.master = self.read_value(args.coverage_docstring_master)
        self.develop = self.read_value(args.coverage_docstring_develop)
        self.feature_value = self.read_value(args.coverage_docstring_feature)

    def format_value(self, value):
        if not value:
            return '0%'
        return value

    def badge(self, value):
        return ''


class GithubWorkflowMetric(BaseMetric):
    def __init__(
        self,
        badge_gen: 'BadgeGenerator',
        workflow_filename: str,
        label: str,
        feature=None,
    ):
        base = Path(workflow_filename).stem.replace('.', '-').replace('_', '-')
        key = base
        super().__init__(badge_gen, key=key, label=label, feature=feature)
        self.workflow_filename = workflow_filename

    @staticmethod
    def _env_key(base: str, branch: str) -> str:
        return f'CI_WORKFLOW_{base.upper().replace("-", "_")}_{branch.upper()}'

    def read_all(self, args):
        base = self.key
        self.master = os.environ.get(self._env_key(base, 'master'), '')
        self.develop = os.environ.get(self._env_key(base, 'develop'), '')
        self.feature_value = os.environ.get(self._env_key(base, 'feature'), '')

    def badge(self, value):
        return self.badge_gen.github_badge(self.workflow_filename, value)

    def refs(self):
        return {
            'master': self.badge('master'),
            'master_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
            'develop': self.badge('develop'),
            'develop_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
            'feature': self.badge(self.feature),
            'feature_url': f'{self.badge_gen.github_workflows}/{self.workflow_filename}',
        }


class CodeFactorMetric(BaseMetric):
    key = 'codefactor'
    label = 'Code quality from CodeFactor.io'

    def __init__(self, badge_gen: BadgeGenerator, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_all(self, args):
        self.master = os.environ.get('CI_CODEFACTOR_MASTER', '')
        self.develop = os.environ.get('CI_CODEFACTOR_DEVELOP', '')
        self.feature_value = os.environ.get('CI_CODEFACTOR_FEATURE', '')

    def badge(self, value):
        return self.badge_gen.codefactor_badge(value)

    def refs(self):
        cf = self.badge_gen.codefactor
        return {
            'master': self.badge('master'),
            'master_url': f'{cf}/overview',
            'develop': self.badge('develop'),
            'develop_url': f'{cf}/overview/develop',
            'feature': self.badge(self.feature),
            'feature_url': f'{cf}/overview/{self.feature}',
        }


class CodecovMetric(BaseMetric):
    key = 'codecov'
    label = 'Unit test coverage from Codecov.io'

    def __init__(self, badge_gen: BadgeGenerator, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    def read_all(self, args):
        self.master = os.environ.get('CI_CODECOV_MASTER', '')
        self.develop = os.environ.get('CI_CODECOV_DEVELOP', '')
        self.feature_value = os.environ.get('CI_CODECOV_FEATURE', '')


class LinesOfCodeMetric(BaseMetric):
    key = 'loc'
    label = 'Source/Logical lines of code'

    def __init__(self, badge_gen: BadgeGenerator, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _sum_raw_metrics(path: Optional[str]) -> Optional[Tuple[int, int]]:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        sloc = 0
        lloc = 0

        def add_from(obj: Any):
            nonlocal sloc, lloc
            if isinstance(obj, dict):
                if 'sloc' in obj or 'lloc' in obj:
                    try:
                        sloc += int(obj.get('sloc', 0))
                        lloc += int(obj.get('lloc', 0))
                    except Exception as exc:
                        logging.debug('raw-metrics sloc/lloc parse error: %s', exc)
                raw = obj.get('raw') if isinstance(obj.get('raw'), dict) else None
                if raw:
                    try:
                        sloc += int(raw.get('sloc', 0))
                        lloc += int(raw.get('lloc', 0))
                    except Exception as exc:
                        logging.debug('raw-metrics raw.sloc/lloc parse error: %s', exc)
                for v in obj.values():
                    if isinstance(v, (dict, list)):
                        add_from(v)
            elif isinstance(obj, list):
                for it in obj:
                    add_from(it)

        add_from(data)
        return (sloc, lloc)

    def read_all(self, args):
        self.master = self._sum_raw_metrics(getattr(args, 'raw_metrics_master', None))
        self.develop = self._sum_raw_metrics(getattr(args, 'raw_metrics_develop', None))
        self.feature_value = self._sum_raw_metrics(getattr(args, 'raw_metrics_feature', None))


class FileCountMetric(BaseMetric):
    key = 'files'
    label = 'Number of files'

    def __init__(self, badge_gen: BadgeGenerator, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _count_files(path: Optional[str]) -> Optional[int]:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        if isinstance(data, dict):
            return len([k for k, v in data.items() if isinstance(v, list)])
        return None

    def read_all(self, args):
        self.master = self._count_files(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._count_files(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._count_files(
            getattr(args, 'cyclomatic_complexity_feature', None)
        )


class FunctionCountMetric(BaseMetric):
    key = 'funcs'
    label = 'Number of functions'

    def __init__(self, badge_gen: BadgeGenerator, feature=None):
        super().__init__(badge_gen, key=self.key, label=self.label, feature=feature)

    @staticmethod
    def _count_functions(path: Optional[str]) -> Optional[int]:
        if not path or not Path(path).exists():
            return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except Exception:
            return None
        total = 0
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    total += len(v)
        return total if total else None

    def read_all(self, args):
        self.master = self._count_functions(getattr(args, 'cyclomatic_complexity_master', None))
        self.develop = self._count_functions(getattr(args, 'cyclomatic_complexity_develop', None))
        self.feature_value = self._count_functions(
            getattr(args, 'cyclomatic_complexity_feature', None)
        )
