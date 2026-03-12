"""Simulation module for generating and exporting synthetic data."""

from ..config.distributions import ProbabilityDistribution, ProbabilitySegment
from .export import DataExporter, DataTransformer, ExportConfig, OutputFormat, OutputLayout
from .generation_result import GenerationResult
from .generator import DataGenerator
from .loader import SimulationDataLoader
from .runtime import (
    ConditionHistoryExportAdapter,
    ConditionHistoryStore,
    CriticalStatePausePolicy,
    EntityRuntimeState,
    SimulationClock,
    SimulationSession,
    TickSize,
    TickUnit,
)

__all__ = [
    # Distributions
    "ProbabilityDistribution",
    "ProbabilitySegment",
    # Generator
    "DataGenerator",
    "GenerationResult",
    "SimulationDataLoader",
    "SimulationClock",
    "SimulationSession",
    "TickSize",
    "TickUnit",
    "EntityRuntimeState",
    "CriticalStatePausePolicy",
    "ConditionHistoryStore",
    "ConditionHistoryExportAdapter",
    # Export
    "DataExporter",
    "ExportConfig",
    "DataTransformer",
    "OutputFormat",
    "OutputLayout",
]
