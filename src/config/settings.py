"""Immutable configuration settings for MIDAS.

Configuration is loaded once and passed to services via dependency injection.
"""

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .reference_data import FacilityType, InstallationLocation, SystemType

if TYPE_CHECKING:
    from .distributions import BaseDistribution, ProbabilityDistribution


@dataclass(frozen=True)
class DegradationSettings:
    """Settings related to degradation thresholds and calculations."""

    condition_index_degraded_threshold: float = 25.0
    resiliency_grade_threshold: int = 70
    initial_condition_index: float = 99.99
    max_time_series_years: int = 10


@dataclass(frozen=True)
class SimulationSettings:
    """Settings for data simulation/generation."""

    facilities_per_installation: tuple[int, int] = (8, 14)
    dependency_chain_group_range: tuple[int, int] = (1, 3)
    max_vertical_depth: int = 3  # How many vertical levels (e.g. 3 = A/B/C, 5 = A-E)
    maximum_system_age: int = 80
    maximum_facility_age: int = 80
    facility_condition_randomly_degrades_chance: int = 35

    def get_random_facility_count(self):
        """Get a random number in the configured range to use for Facility generation.
        """
        return random.randint(*self.facilities_per_installation)

    def get_dependency_chain_vertical_positions(self) -> list[str]:
        """Return dependency-chain vertical labels based on max depth.

        For example, a max depth of 3 returns ``["A", "B", "C"]``.
        Falls back to the same default when the configured value is invalid.
        """
        max_depth = getattr(self, "max_vertical_depth", None)
        if isinstance(max_depth, int) and max_depth > 0:
            return [chr(ord("A") + i) for i in range(max_depth)]
        else:
            return ["A", "B", "C"]

    def get_random_dependency_chain_vertical_position(self) -> str:
        """Return a random vertical position from configured dependency levels."""
        return random.choice(self.get_dependency_chain_vertical_positions())

    def get_random_dependency_chain_group_count(self) -> int:
        """Return a random dependency-group count from the configured range.

        This is the number of groups to assign, not the group IDs.
        """
        return random.randint(*self.dependency_chain_group_range)

    def get_random_dependency_chain_group_IDS(self) -> list[int]:
        """Return sorted unique dependency-group IDs for a dependency chain.

        The number of IDs is randomly determined using the configured dependency_chain_group_range
        and the result of get_random_dependency_chain_group_count(). IDs are selected randomly
        from the inclusive range specified by dependency_chain_group_range.

        If the range is (0, 0), an empty list is returned.
        """
        lower, upper = self.dependency_chain_group_range
        if upper < lower:
            lower, upper = upper, lower
        id_pool = list(range(max(1, lower), upper + 1))
        if not id_pool:
            return []
        sample_count = min(self.get_random_dependency_chain_group_count(), len(id_pool))
        return sorted(random.sample(id_pool, sample_count))


@dataclass(frozen=True)
class OutputSettings:
    """Settings for data export/output."""

    excel_sheet_main: str = "Main Data"
    excel_sheet_facility_ts: str = "Facility Time Series"
    excel_sheet_system_ts: str = "System Time Series"
    excel_sheet_metadata: str = "_metadata"
    metadata_file_suffix: str = "_metadata.json"
    csv_table_separator: str = "_"
    excel_sheet_work_orders: str = "Work Orders"


@dataclass
class SimulationDistributions:
    """Probability distributions for simulation data generation.

    These distributions control how random values are generated for
    condition indices, ages, and resiliency grades.
    """

    condition_index: "ProbabilityDistribution | None" = None
    age: "ProbabilityDistribution | None" = None
    grade: "ProbabilityDistribution | None" = None
    work_order_count: "BaseDistribution | None" = None
    work_order_status: "ProbabilityDistribution | None" = None
    work_order_priority: "ProbabilityDistribution | None" = None
    work_order_requesting_organization: "ProbabilityDistribution | None" = None

    def __post_init__(self) -> None:
        """Initialize default distributions if not provided."""
        from .distributions import (
            BathtubCurveDistribution,
            ProbabilityDistribution,
            ProbabilitySegment,
        )

        if self.condition_index is None:
            object.__setattr__(
                self,
                "condition_index",
                ProbabilityDistribution(
                    [
                        ProbabilitySegment(7, "1-50"),
                        ProbabilitySegment(88, "50-85"),
                        ProbabilitySegment(5, "85-100"),
                    ]
                ),
            )

        if self.age is None:
            object.__setattr__(
                self,
                "age",
                ProbabilityDistribution(
                    [
                        ProbabilitySegment(50, "20-40"),
                        ProbabilitySegment(20, "10-20"),
                        ProbabilitySegment(20, "41-80"),
                        ProbabilitySegment(10, "0-9"),
                    ]
                ),
            )

        if self.grade is None:
            object.__setattr__(
                self,
                "grade",
                ProbabilityDistribution(
                    [
                        ProbabilitySegment(52, "1"),
                        ProbabilitySegment(32, "2"),
                        ProbabilitySegment(12, "3"),
                        ProbabilitySegment(4, "4"),
                    ]
                ),
            )

        if self.work_order_count is None:
            object.__setattr__(self, "work_order_count", BathtubCurveDistribution())

        if self.work_order_status is None:
            object.__setattr__(
                self,
                "work_order_status",
                ProbabilityDistribution(
                    [
                        ProbabilitySegment(8, "Submitted"),
                        ProbabilitySegment(14, "Approved"),
                        ProbabilitySegment(26, "In Progress"),
                        ProbabilitySegment(52, "Completed"),
                    ]
                ),
            )

        if self.work_order_priority is None:
            object.__setattr__(
                self,
                "work_order_priority",
                ProbabilityDistribution(
                    [
                        ProbabilitySegment(7, "Emergency"),
                        ProbabilitySegment(18, "Urgent"),
                        ProbabilitySegment(50, "Routine"),
                        ProbabilitySegment(25, "Maintenance"),
                    ]
                ),
            )

        if self.work_order_requesting_organization is None:
            object.__setattr__(
                self,
                "work_order_requesting_organization",
                ProbabilityDistribution(
                    [
                        ProbabilitySegment(1, "J1"),
                        ProbabilitySegment(1, "J2"),
                        ProbabilitySegment(1, "J3"),
                        ProbabilitySegment(1, "J4"),
                        ProbabilitySegment(1, "J5"),
                        ProbabilitySegment(1, "J6"),
                    ]
                ),
            )


@dataclass
class MIDASSettings:
    """Main configuration container for MIDAS application.

    This is the single source of truth for configuration. Create once
    at application startup and pass to services.
    """

    degradation: DegradationSettings = field(default_factory=DegradationSettings)
    simulation: SimulationSettings = field(default_factory=SimulationSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    distributions: SimulationDistributions = field(default_factory=SimulationDistributions)

    # Reference data (loaded from Excel)
    facility_types: dict[int, FacilityType] = field(default_factory=dict)
    system_types: dict[int, SystemType] = field(default_factory=dict)
    installation_locations: list[InstallationLocation] = field(default_factory=list)
    config_workbook_path: Path | None = None

    # Pre-loaded work-order text (system_type_title_lower -> list of triplets)
    work_order_text_cache: dict[str, list[tuple[str, str, str]]] = field(default_factory=dict)

    def get_facility_type(self, key: int) -> FacilityType | None:
        """Get facility type by key."""
        return self.facility_types.get(key)

    def get_system_type(self, key: int) -> SystemType | None:
        """Get system type by key."""
        return self.system_types.get(key)

    def get_random_facility_type(self, excluded_keys: list[int] | None = None) -> FacilityType | None:
        """Get a random facility type, optionally excluding certain keys."""
        excluded = excluded_keys or []
        available = [ft for ft in self.facility_types.values() if ft.key not in excluded]
        return random.choice(available) if available else None

    def get_random_system_type_for_facility(self, facility_key: int) -> "SystemType | None":
        """Get a random system type that belongs to the given facility type."""
        system_types = self.get_system_types_for_facility(facility_key)
        return random.choice(system_types) if system_types else None

    def get_system_types_for_facility(self, facility_key: int) -> list[SystemType]:
        """Get all system types that belong to a facility type."""
        return [st for st in self.system_types.values() if facility_key in st.facility_keys]

    def get_random_location(self) -> InstallationLocation | None:
        """Get a random location from loaded installation locations."""
        return random.choice(self.installation_locations) if self.installation_locations else None

    def get_random_work_order_requesting_organization(self) -> str | None:
        """Get a random requesting organization from configured distribution."""
        sampled = self.distributions.work_order_requesting_organization.sample()
        text = str(sampled).strip() if sampled is not None else ""
        return text or None

    def sample_work_order_text(self, system_type: str | None) -> tuple[str, str, str] | None:
        """Return a random work-order text triplet from the pre-loaded cache."""
        if not self.work_order_text_cache:
            return None

        key = system_type.strip().lower() if system_type else None
        rows = self.work_order_text_cache.get(key) if key else None
        if rows is None:
            rows = self.work_order_text_cache.get("_fallback")
        if not rows:
            return None

        return random.choice(rows)

    @classmethod
    def with_defaults(cls) -> "MIDASSettings":
        """Create settings with all defaults (no reference data)."""
        return cls()

    @classmethod
    def from_excel(cls, path: Path) -> "MIDASSettings":
        """Load settings from Excel configuration file.

        Args:
            path: Path to midas_config_values.xlsx

        Returns:
            Configured MIDASSettings instance.

        """
        from .loader import load_settings_from_excel

        return load_settings_from_excel(path)

    @classmethod
    def default_config_path(cls) -> Path:
        """Get the default configuration file path."""
        return Path(__file__).parent / "midas_config_values.xlsx"
