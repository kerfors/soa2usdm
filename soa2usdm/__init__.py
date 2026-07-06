"""
SoA2USDM library — core processing logic.

Steps:
    apply_corrections   Layer 1.5 — apply human corrections to raw extraction (ApplyCorrectionsStep)
    resolve             Layer 2 — IDs, hierarchy, validation (ResolveStep)
    consolidate         Layer 3 — cross-table integration (ConsolidateStep)
    visualize           Consolidated HTML generation (VisualizeStep)
    visualize_resolved  Per-table resolved HTML, debugging (VisualizeResolvedStep)
    index_generator     Collection index page (IndexGeneratorStep)
"""

from . import config
from .errors import Errors
from .analytics import Analytics
from .base import PipelineStepBase
from .corrections import ApplyCorrectionsStep, apply_corrections
from .resolve import ResolveStep
from .consolidate import ConsolidateStep
from .visualize import VisualizeStep
from .visualize_resolved import VisualizeResolvedStep
from .index_generator import IndexGeneratorStep

__version__ = "0.1.0"

__all__ = [
    "config",
    "Errors",
    "Analytics",
    "PipelineStepBase",
    "ApplyCorrectionsStep",
    "apply_corrections",
    "ResolveStep",
    "ConsolidateStep",
    "VisualizeStep",
    "VisualizeResolvedStep",
    "IndexGeneratorStep",
]
