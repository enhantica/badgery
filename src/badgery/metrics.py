"""Metric readers and adapters used by the dashboard renderer.

This module re-exports metric classes from lightweight submodules to
keep per-file complexity low and improve maintainability.
"""

from __future__ import annotations

from badgery._metrics.base import BaseMetric
from badgery._metrics.codecov import CodecovMetric
from badgery._metrics.codefactor import CodeFactorMetric
from badgery._metrics.complexity import ComplexityMetric
from badgery._metrics.counts import FileCountMetric
from badgery._metrics.counts import FunctionCountMetric
from badgery._metrics.counts import FunctionsPerFileMetric
from badgery._metrics.docstring import DocstringCoverageMetric
from badgery._metrics.loc import LinesOfCodeMetric
from badgery._metrics.maintainability import MaintainabilityMetric
from badgery._metrics.workflow import GithubWorkflowMetric

__all__ = [
    'BaseMetric',
    'CodeFactorMetric',
    'CodecovMetric',
    'ComplexityMetric',
    'DocstringCoverageMetric',
    'FileCountMetric',
    'FunctionCountMetric',
    'FunctionsPerFileMetric',
    'GithubWorkflowMetric',
    'LinesOfCodeMetric',
    'MaintainabilityMetric',
]
