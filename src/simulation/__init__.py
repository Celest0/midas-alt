"""Simulation module for generating and exporting synthetic data."""

from ..config.distributions import ProbabilityDistribution, ProbabilitySegment
from .export import DataExporter, DataTransformer, ExportConfig, OutputFormat, OutputLayout
from .generation_result import GenerationResult
from .generator import DataGenerator

__all__ = [
    # Distributions
    "ProbabilityDistribution",
    "ProbabilitySegment",
    # Generator
    "DataGenerator",
    "GenerationResult",
    # Export
    "DataExporter",
    "ExportConfig",
    "DataTransformer",
    "OutputFormat",
    "OutputLayout",
]
