"""Typed results for simulation data generation."""

from dataclasses import dataclass, field

from ..models import Facility, Installation, System
from ..models.work_order import WorkOrder


@dataclass
class GenerationResult:
    """Container for generated entities across hierarchy levels."""

    installations: list[Installation] = field(default_factory=list)
    facilities: list[Facility] = field(default_factory=list)
    systems: list[System] = field(default_factory=list)
    work_orders: list[WorkOrder] = field(default_factory=list)

    @classmethod
    def from_single_installation(
        cls,
        installation: Installation,
        facilities: list[Facility],
        systems: list[System],
        work_orders: list[WorkOrder],
    ) -> "GenerationResult":
        """Build a result object for a single generated installation."""
        return cls(
            installations=[installation],
            facilities=facilities,
            systems=systems,
            work_orders=work_orders,
        )
