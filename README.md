# MIDAS

MIDAS (**M**ission **I**nfrastructure **D**egradation **A**nalysis **S**imulation) generates synthetic installation infrastructure data for exploration and export.  
It models `Installation -> Facility -> System -> WorkOrder`, is configured from Excel, and is operated through an interactive CLI.

## Quick Start

```bash
uv venv
source .venv/bin/activate
uv run python main.py
```

At startup MIDAS loads configuration from `src/config/midas_config_values.xlsx`, preloads `Work Order Text` samples into an in-memory cache for fast generation, initializes app state, and opens the main menu.
`Run Time Simulation` is the first main-menu option and is now the primary user entrypoint.

### Requirements

- Python >= 3.11
- Runtime: `pandas[excel]`, `rich`, `numpy`, `scikit-learn`
- Dev: `pytest`, `pytest-cov`, `ruff`, `docformatter`

## Primary Workflow

The primary path through the application is:

1. Launch MIDAS.
2. Select `Run Time Simulation` from the main menu.
3. Choose either:
   - load a normalized CSV dataset directory or normalized XLSX workbook exported by `src/simulation/export/`
   - generate a default installation hierarchy in memory
4. If multiple installations are loaded, choose which installation to simulate.
5. Start from the live simulation dashboard, which opens paused by default.

The live dashboard currently provides:

- current simulated date
- run state, tick size, and playback speed
- installation condition index and aggregate degraded/inoperable counts
- work-order counts by status
- a facility dependency graph with systems hidden by default
- focused inspection of an installation, facility, or system
- keyboard controls for pause/resume, single-step, speed changes, tick-size changes, inspection, graph expansion, help, and quit

The current runtime does not yet degrade condition index values on its own. It provides the clock, history tracking, pause hooks, and CLI shell needed for incremental implementation of that logic.

## Architecture

### `src/functions`

- `generate_id.py`: UUID-based ID generation used by all model dataclasses.
- `configure_logging.py`: application logging setup (env-driven log level, console handler).

### `src/cli`

- `cli.py` initializes config/app state and launches the menu system.
- `menu/` contains the reusable menu framework (`MenuBuilder`, `MenuHandler`, `MenuItem`) and now exposes `Run Time Simulation` as the first main-menu action.
- `handlers/config_handlers.py` shows loaded config/reference summaries and supports reload.
- `handlers/simulate_handlers.py` provides:
  - load-or-generate runtime simulation entrypoint
  - interactive hierarchy browsing (`Installation -> Facility -> System -> WorkOrder`)
  - quick generation stats
  - guided dataset export wizard
- `simulation_shell.py` renders the live Rich dashboard for time-stepped simulation, including the graph view, inspection panel, and keyboard controls.
- `utils/` shared CLI helpers:
  - `display.py`: `DisplayHelper` -- panels, tables, and status messages via Rich
  - `input.py`: `InputHelper` -- prompts, yes/no, choice selection, number validation
  - `navigation.py`: `NavigationHelper` -- step progress display, back-command detection

### `src/models`

- `installation.py`: top-level site model (`facility_ids`, aggregate `condition_index`)
- `facility.py`: facility model (`dependency_position`, `resiliency_grade`, `system_ids`)
- `system.py`: system model (`facility_id`, `work_orders`)
- `work_order.py`: work-order model (`status`, `priority`, `trade`, `requesting_organization`, `work_category`, `room_area`, timestamps, text fields, `impacts_mission`)
- `dependency_position.py`: hierarchy coordinates (`vertical_position`, `group_ids`)

### `src/enums`

- `ufc_grade.py`: UFC resiliency grades `G1..G4`
- `work_order.py`: `WO_Status`, `WO_Priority`, `WO_TradeSkill`
- `entity_type.py`: shared entity typing enum

### `src/config`

- `settings.py`: typed settings groups + reference collections in `MIDASSettings`, including workbook-backed work-order text sampling via an in-memory `work_order_text_cache`
- `loader.py`: Excel loader/parsers for config, reference data, distributions, and eager `Work Order Text` cache construction at startup
- `distributions.py`: distribution system -- `ProbabilitySegment`/`ProbabilityDistribution` (weighted sampling), `EventRateDistribution` with `NormalCurve`, `BathtubCurve`, and `PiecewiseCurve` implementations, plus `DistributionContext` (age, life expectancy, CI)
- `app_state.py`: runtime singleton state (`get_app_state`, reload handling)
- `display.py`: Rich-based display helpers (`create_facility_types_table`, `create_system_types_table`, `create_installation_locations_table`, `create_config_values_panel`)
- `reference_data.py`: `FacilityType`, `SystemType`, `InstallationLocation`, `WorkOrderText`

### `src/simulation`

- `generator.py`: public facade (`DataGenerator`)
- `loader.py`: `SimulationDataLoader` for rehydrating normalized CSV/XLSX exports into domain objects
- `distributions.py`: re-export layer (canonical logic lives in `src/config/distributions.py`)
- `modules/base.py`: abstract simulation-module contract plus `ModuleEvent` for tick-time logic and pause signaling
- `generation_result.py`: typed `GenerationResult` contract with:
  - `installations`
  - `facilities`
  - `systems`
  - `work_orders`
- `runtime/`:
  - `clock.py`: simulation clock, tick sizes, and tick-size presets
  - `history.py`: `ConditionHistoryStore` and `ConditionHistoryExportAdapter` for runtime historical CI storage
  - `session.py`: `SimulationSession`, runtime aggregate recomputation, focus state, work-order summaries, and critical pause policy
- `data_generation/` responsibility split:
  - `install_generator.py`
  - `facility_generator.py`
  - `system_generator.py`
  - `work_order_generator.py`
  - `data_generator_base.py` (shared sampling/context)
- `export/`:
  - `exporter.py`: `DataExporter` -- generates data and delegates to a formatter
  - `config.py`: `ExportConfig` dataclass (file name, format, directory, layout, time-series, metadata)
  - `transformers.py`: `DataTransformer` -- domain entities to normalized/denormalized DataFrames
  - `enums.py`: `OutputFormat` (CSV, XLSX), `OutputLayout` (NORMALIZED, DENORMALIZED)
  - formatters: `csv_formatter.py`, `excel_formatter.py` (JSON output removed)

## Generation Flow

```text
InstallGenerator
  -> FacilityGenerator
    -> SystemGenerator
      -> WorkOrderGenerator
        -> GenerationResult
```

Key behaviors:

- Installation CI is aggregated from facility CI.
- Facility CI is aggregated from system CI.
- Facility dependency positions are validated to maintain a valid hierarchy.
- Facility resiliency grades are derived from dependency relationships + threshold settings.
- Work-order counts/status/priority are sampled from configured distributions.
- Work-order text samples are read once from the workbook at startup and then sampled from memory during generation.

## Runtime Simulation Flow

```text
LoadedOrGeneratedData
  -> SimulationDataLoader / DataGenerator
    -> SimulationSession
      -> SimulationClock
      -> Runtime Modules
      -> Aggregate CI Recalculation
      -> ConditionHistoryStore
      -> CriticalStatePausePolicy
      -> Rich SimulationShell
```

Key runtime behaviors:

- The session simulates exactly one active installation at a time.
- The simulation clock advances in configurable steps (`day`, `week`, `month`, `year`).
- Each tick recalculates facility and installation CI from current child entities.
- Historical CI is stored as runtime snapshots in `ConditionHistoryStore`.
- The runtime starts paused and can be advanced continuously or one tick at a time.
- Systems are hidden by default in the graph view and appear when explicitly toggled or focused.
- A pause policy exists for newly critical entities so future degradation logic can stop the simulation when mission-impacting failures occur.

## Configuration

All runtime behavior is driven by `src/config/midas_config_values.xlsx`.
The `Work Order Text` sheet is loaded once at startup and cached in memory so work-order generation does not repeatedly re-read Excel data.

Important configurable groups:

- simulation ranges (facility counts, max ages, dependency settings)
- degradation thresholds
- output naming (CSV separator + Excel sheet names)
- distributions:
  - condition index
  - age
  - grade
  - work-order count/status/priority/requesting organization
- work-order text samples from the `Work Order Text` sheet (cached in memory at startup)

Defaults in `settings.py` are used if values are absent or invalid during load.
The current runtime shell already reads degradation thresholds for status labeling and pause-policy decisions, but it does not yet apply a degradation formula to change CI values over time.

## Export Features

- Output formats: `csv`, `xlsx`
- Layouts:
  - `normalized`: separate tables/sheets
  - `denormalized`: flattened table
- Work orders are included in both layouts.
- Optional facility/system time-series data in the current exporter.
- Optional metadata output.

Important note about time series:

- The legacy export path still back-calculates facility/system time-series values from current CI and age inside `src/simulation/export/transformers.py`.
- The new runtime simulation stores real per-tick historical CI snapshots in `ConditionHistoryStore`.
- The intended next step is to replace the exporter's synthetic time-series generation with `ConditionHistoryExportAdapter` output from a simulation session.

## Example Usage

```python
from pathlib import Path
from src.config import MIDASSettings
from src.simulation import DataExporter, DataGenerator, SimulationSession

settings = MIDASSettings.from_excel(Path("src/config/midas_config_values.xlsx"))
generator = DataGenerator(settings=settings, seed=42)

result = generator.generate_installation()
print(len(result.installations), len(result.facilities), len(result.systems), len(result.work_orders))

session = SimulationSession.from_generation_result(result, settings=settings)
session.step()
history_tables = session.export_history_tables()
print(history_tables["facility_time_series"].head())

exporter = DataExporter(
    file_name="sample_data",
    output_format="xlsx",  # or "csv"
    output_directory="./output",
    layout="normalized",
    include_time_series=False,
    generate_metadata=True,
    settings=settings,
)
path = exporter.generate_and_export(method="default")
print(path)
```

Loading previously exported normalized data back into the runtime:

```python
from pathlib import Path
from src.config import MIDASSettings
from src.simulation import SimulationDataLoader, SimulationSession

settings = MIDASSettings.from_excel(Path("src/config/midas_config_values.xlsx"))
loader = SimulationDataLoader(settings=settings)
result = loader.load(Path("./output/sample_data"))

session = SimulationSession.from_generation_result(
    result,
    settings=settings,
    installation_id=result.installations[0].id,
)
print(session.current_date, session.installation.condition_index)
```

## Continuing Condition Index Implementation

The runtime scaffolding is in place; the next CI work should happen in simulation modules rather than in the export layer.

Recommended approach:

1. Add a new module under `src/simulation/modules/` for each focused behavior.
   - Example responsibilities: system CI degradation, work-order lifecycle progression, repair effects, mission-impact evaluation.
2. Implement each module against the `Base.apply(session) -> list[ModuleEvent]` contract in `src/simulation/modules/base.py`.
3. Mutate system-level state first inside the module.
   - `SimulationSession` already recalculates facility and installation CI after module execution, so parent aggregates should continue to be derived from children.
4. Use `session.current_date` and `session.clock.tick_size` to scale logic by the active tick size.
   - Day-based logic can be multiplied or accumulated for week/month/year ticks rather than branching the CLI.
5. Use `session.work_orders`, `session.work_orders_by_system`, and `session.systems` when degradation depends on open maintenance work or mission impact.
6. Emit `ModuleEvent(..., should_pause=True)` when a module detects a condition that should stop playback immediately.
   - The built-in `CriticalStatePausePolicy` can also pause after state changes when an entity becomes newly inoperable or mission blocked.
7. Keep historical CI storage in the runtime layer.
   - Do not write directly to export-only time-series tables during simulation.
   - Let `ConditionHistoryStore` capture snapshots and `ConditionHistoryExportAdapter` shape that history for later export.
8. When the degradation logic is stable, replace the synthetic `_generate_facility_time_series()` / `_generate_system_time_series()` flow in `src/simulation/export/transformers.py` with runtime history generated from real simulation sessions.

Suggested first CI module:

- compute a daily CI delta at the `System` level
- clamp CI to a valid range
- optionally open or escalate work orders based on thresholds
- let session aggregate recalculation propagate updated CI to facilities and installations
- rely on the existing pause policy once a system or parent becomes critical

## Tests

- `tests/conftest.py`: shared fixtures
- `tests/integration/test_config_loading_integration.py`: config loading from Excel
- `tests/integration/test_generation_and_export_integration.py`: end-to-end generation and export
- `tests/integration/test_simulation_loader_integration.py`: normalized CSV/XLSX round-trip loading
- `tests/integration/test_simulation_runtime_integration.py`: session ticking, history capture, and pause-policy behavior
- `tests/integration/test_simulation_cli_integration.py`: CLI helper behavior, menu placement, and controls help

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

Focused simulation checks:

```bash
uv run pytest tests/integration/test_simulation_loader_integration.py
uv run pytest tests/integration/test_simulation_runtime_integration.py
uv run pytest tests/integration/test_simulation_cli_integration.py
```
