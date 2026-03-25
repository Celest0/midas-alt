"""Enums for export configuration."""

from enum import Enum


class OutputFormat(Enum):
    """Output file format options."""

    CSV = "csv"
    XLSX = "xlsx"


class OutputLayout(Enum):
    """Data layout options for export."""

    NORMALIZED = "normalized"  # Separate tables for installations, facilities, systems
    DENORMALIZED = "denormalized"  # Single flattened table
