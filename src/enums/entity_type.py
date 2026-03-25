from enum import Enum


class EntityType(Enum):
    """Type of domain entity for ML feature extraction."""

    INSTALLATION = "installation"
    FACILITY = "facility"
    SYSTEM = "system"
