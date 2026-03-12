"""Integration tests for simulation session ticking and history."""

from datetime import date

from src.config.settings import MIDASSettings
from src.enums.entity_type import EntityType
from src.simulation import DataGenerator, SimulationSession
from src.simulation.modules.base import Base


def _loaded_settings() -> MIDASSettings:
    """Load workbook-backed settings for realistic integration coverage."""
    return MIDASSettings.from_excel(MIDASSettings.default_config_path())


class ForceInoperableModule(Base):
    """Test module that forces one system into an inoperable state once."""

    def __init__(self) -> None:
        """Track whether the critical transition has already been applied."""
        self._applied = False

    def apply(self, session: SimulationSession):
        """Force the first system to become inoperable."""
        if self._applied:
            return []
        session.systems[0].condition_index = 0.0
        self._applied = True
        return []


def test_session_records_history_and_advances_dates_without_ci_changes() -> None:
    """Ticking should advance dates and append stable CI snapshots when no modules run."""
    settings = _loaded_settings()
    result = DataGenerator(settings=settings, seed=42).generate_installation()
    initial_installation_ci = result.installations[0].condition_index
    initial_facility_cis = {facility.id: facility.condition_index for facility in result.facilities}
    initial_system_cis = {system.id: system.condition_index for system in result.systems}

    session = SimulationSession.from_generation_result(
        result=result,
        settings=settings,
        start_date=date(2026, 1, 1),
    )

    initial_snapshot_count = 1 + len(session.facilities) + len(session.systems)
    assert session.current_date == date(2026, 1, 1)
    assert len(session.history.snapshots) == initial_snapshot_count

    session.resume()
    session.step()
    session.step()

    assert session.current_date == date(2026, 1, 3)
    assert session.clock.tick_index == 2
    assert len(session.history.snapshots) == initial_snapshot_count * 3
    assert session.installation.condition_index == initial_installation_ci
    assert {facility.id: facility.condition_index for facility in session.facilities} == initial_facility_cis
    assert {system.id: system.condition_index for system in session.systems} == initial_system_cis

    tables = session.export_history_tables()
    assert tables["installation_time_series"] is not None
    assert tables["facility_time_series"] is not None
    assert tables["system_time_series"] is not None
    assert len(tables["installation_time_series"]) == 3
    assert len(tables["facility_time_series"]) == len(session.facilities) * 3
    assert len(tables["system_time_series"]) == len(session.systems) * 3


def test_session_pause_policy_emits_event_for_newly_inoperable_entity() -> None:
    """Pause policies should fire when a module pushes an entity into a critical state."""
    settings = _loaded_settings()
    result = DataGenerator(settings=settings, seed=42).generate_installation()
    result.systems[0].condition_index = 50.0

    session = SimulationSession.from_generation_result(
        result=result,
        settings=settings,
        start_date=date(2026, 1, 1),
        modules=[ForceInoperableModule()],
    )

    session.resume()
    events = session.step()

    assert session.paused is True
    assert session.stop_reason is not None
    assert any(event.should_pause for event in events)
    assert any(event.entity_type == EntityType.SYSTEM for event in events if event.should_pause)
