"""Integration tests for Excel-backed configuration loading."""

from pathlib import Path

import pytest

from src.config.app_state import ApplicationState
from src.config.distributions import EventRateDistribution, ProbabilityDistribution
from src.config.loader import ConfigLoadError
from src.config.settings import MIDASSettings


def _loaded_settings() -> MIDASSettings:
    """Load workbook-backed settings for reuse across tests."""
    return MIDASSettings.from_excel(MIDASSettings.default_config_path())


# ---------------------------------------------------------------------------
# Existing tests
# ---------------------------------------------------------------------------


def test_default_config_path_exists() -> None:
    """Ensure the expected Excel configuration workbook is present."""
    config_path = MIDASSettings.default_config_path()
    assert config_path.exists(), f"Expected config workbook at {config_path}"


def test_load_settings_from_excel_populates_expected_containers() -> None:
    """Load settings from workbook and verify core config shapes."""
    settings = _loaded_settings()

    assert isinstance(settings.facility_types, dict)
    assert isinstance(settings.system_types, dict)
    assert isinstance(settings.installation_locations, list)
    assert isinstance(settings.config_workbook_path, Path)
    assert settings.config_workbook_path.exists()

    assert settings.facility_types, "Expected at least one facility type"
    assert settings.system_types, "Expected at least one system type"
    assert settings.installation_locations, "Expected at least one installation location"


def test_work_order_requesting_organization_distribution_is_available() -> None:
    """Requesting organization distribution should load from config/defaults."""
    settings = _loaded_settings()
    samples = {settings.get_random_work_order_requesting_organization() for _ in range(24)}
    assert samples
    assert samples.issubset({"J1", "J2", "J3", "J4", "J5", "J6"})


# ---------------------------------------------------------------------------
# Scalar settings loaded from workbook
# ---------------------------------------------------------------------------


def test_degradation_settings_values_match_workbook() -> None:
    """DegradationSettings fields should be numeric and within reasonable ranges."""
    settings = _loaded_settings()
    deg = settings.degradation

    assert isinstance(deg.condition_index_degraded_threshold, (int, float))
    assert 0 < deg.condition_index_degraded_threshold <= 100

    assert isinstance(deg.resiliency_grade_threshold, int)
    assert 0 < deg.resiliency_grade_threshold <= 100

    assert isinstance(deg.initial_condition_index, (int, float))
    assert 0 < deg.initial_condition_index <= 100

    assert isinstance(deg.max_time_series_years, int)
    assert deg.max_time_series_years > 0


def test_simulation_settings_values_match_workbook() -> None:
    """SimulationSettings range/scalar fields should have valid values."""
    settings = _loaded_settings()
    sim = settings.simulation

    low, high = sim.facilities_per_installation
    assert isinstance(low, int) and isinstance(high, int)
    assert 0 < low <= high

    dep_low, dep_high = sim.dependency_chain_group_range
    assert isinstance(dep_low, int) and isinstance(dep_high, int)
    assert 0 < dep_low <= dep_high

    assert isinstance(sim.maximum_system_age, int) and sim.maximum_system_age > 0
    assert isinstance(sim.maximum_facility_age, int) and sim.maximum_facility_age > 0
    assert 0 <= sim.facility_condition_randomly_degrades_chance <= 100


def test_output_settings_values_match_workbook() -> None:
    """OutputSettings fields should be non-empty strings."""
    settings = _loaded_settings()
    out = settings.output

    assert out.excel_sheet_main and isinstance(out.excel_sheet_main, str)
    assert out.excel_sheet_facility_ts and isinstance(out.excel_sheet_facility_ts, str)
    assert out.excel_sheet_system_ts and isinstance(out.excel_sheet_system_ts, str)
    assert out.excel_sheet_work_orders and isinstance(out.excel_sheet_work_orders, str)
    assert out.excel_sheet_metadata and isinstance(out.excel_sheet_metadata, str)
    assert out.metadata_file_suffix and isinstance(out.metadata_file_suffix, str)
    assert out.csv_table_separator and isinstance(out.csv_table_separator, str)
    assert len(out.csv_table_separator) <= 3, "Separator should be short"


# ---------------------------------------------------------------------------
# Reference data field validity
# ---------------------------------------------------------------------------


def test_facility_types_have_valid_fields() -> None:
    """Every loaded FacilityType should have a positive key, non-empty title, and sane numerics."""
    settings = _loaded_settings()

    for key, ft in settings.facility_types.items():
        assert key == ft.key
        assert ft.key > 0, f"FacilityType key must be positive, got {ft.key}"
        assert ft.title and ft.title.strip(), f"FacilityType {ft.key} has empty title"
        assert ft.life_expectancy > 0, f"FacilityType {ft.key} life_expectancy must be positive"
        assert ft.mission_criticality >= 1, f"FacilityType {ft.key} mission_criticality must be >= 1"
        assert ft.life_expectancy_months == ft.life_expectancy * 12


def test_system_types_have_valid_fields_and_facility_key_references() -> None:
    """Every SystemType should reference valid FacilityType keys."""
    settings = _loaded_settings()

    for key, st in settings.system_types.items():
        assert key == st.key
        assert st.key > 0, f"SystemType key must be positive, got {st.key}"
        assert st.title and st.title.strip(), f"SystemType {st.key} has empty title"
        assert st.life_expectancy > 0, f"SystemType {st.key} life_expectancy must be positive"
        assert isinstance(st.facility_keys, tuple), f"SystemType {st.key} facility_keys should be a tuple"
        assert st.facility_keys, f"SystemType {st.key} has no facility_keys"

        for fk in st.facility_keys:
            assert fk in settings.facility_types, (
                f"SystemType {st.key} references facility key {fk} "
                f"which is not in loaded facility_types"
            )


def test_installation_locations_have_valid_fields() -> None:
    """Every InstallationLocation should have non-empty core fields."""
    settings = _loaded_settings()
    assert settings.installation_locations

    for loc in settings.installation_locations:
        assert loc.title and str(loc.title).strip(), f"Location missing title: {loc}"
        assert loc.location and str(loc.location).strip(), f"Location missing location: {loc}"
        assert loc.region and str(loc.region).strip(), f"Location missing region: {loc}"


# ---------------------------------------------------------------------------
# Distribution loading
# ---------------------------------------------------------------------------


def test_all_distributions_are_loaded_and_sampleable() -> None:
    """All 7 distribution slots should be populated and sample without error."""
    settings = _loaded_settings()
    dists = settings.distributions

    assert dists.condition_index is not None
    assert dists.age is not None
    assert dists.grade is not None
    assert dists.work_order_count is not None
    assert dists.work_order_status is not None
    assert dists.work_order_priority is not None
    assert dists.work_order_requesting_organization is not None

    for _ in range(20):
        ci = dists.condition_index.sample()
        assert isinstance(ci, (int, float, str))

        age = dists.age.sample()
        assert isinstance(age, (int, float, str))

        grade = dists.grade.sample()
        assert isinstance(grade, (int, float, str))

    assert isinstance(dists.work_order_count, (ProbabilityDistribution, EventRateDistribution))

    valid_statuses = {"Submitted", "Approved", "In Progress", "Completed"}
    status_samples = {str(dists.work_order_status.sample()).strip() for _ in range(50)}
    assert status_samples.issubset(valid_statuses), f"Unexpected statuses: {status_samples - valid_statuses}"

    valid_priorities = {"Emergency", "Urgent", "Routine", "Maintenance"}
    priority_samples = {str(dists.work_order_priority.sample()).strip() for _ in range(50)}
    assert priority_samples.issubset(valid_priorities), f"Unexpected priorities: {priority_samples - valid_priorities}"

    valid_orgs = {"J1", "J2", "J3", "J4", "J5", "J6"}
    org_samples = {str(dists.work_order_requesting_organization.sample()).strip() for _ in range(50)}
    assert org_samples.issubset(valid_orgs), f"Unexpected orgs: {org_samples - valid_orgs}"


# ---------------------------------------------------------------------------
# ApplicationState and error handling
# ---------------------------------------------------------------------------


def test_application_state_initialize_reports_correct_counts() -> None:
    """ApplicationState.initialize() should succeed and report matching counts."""
    state = ApplicationState.initialize()

    assert state.initialized_successfully
    assert not state.has_errors

    assert state.load_result.facility_types_loaded == len(state.settings.facility_types)
    assert state.load_result.system_types_loaded == len(state.settings.system_types)
    assert state.load_result.installation_locations_loaded == len(state.settings.installation_locations)

    assert state.load_result.facility_types_loaded > 0
    assert state.load_result.system_types_loaded > 0
    assert state.load_result.installation_locations_loaded > 0


def test_load_settings_from_nonexistent_path_raises_config_load_error() -> None:
    """MIDASSettings.from_excel with a bad path should raise ConfigLoadError."""
    with pytest.raises(ConfigLoadError):
        MIDASSettings.from_excel(Path("/tmp/does_not_exist_midas_test.xlsx"))


def test_application_state_with_defaults_uses_fallback_settings() -> None:
    """ApplicationState.with_defaults() should succeed with a warning."""
    state = ApplicationState.with_defaults()

    assert state.initialized_successfully
    assert state.has_warnings
    assert not state.settings.facility_types
    assert not state.settings.system_types
