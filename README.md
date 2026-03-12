# MIDAS

MIDAS (**M**ission **I**nfrastructure **D**egradation **A**nalysis **S**imulation) generates synthetic installation infrastructure data for exploration and export.  
It models `Installation -> Facility -> System -> WorkOrder`, is configured from Excel, and is operated through an interactive CLI.

## Quick Start

```bash
uv venv
source .venv/bin/activate
uv run python main.py
```

At startup MIDAS loads configuration from `src/config/midas_config_values.xlsx`, initializes app state, and opens the main menu.

### Requirements

- Python >= 3.11
- Runtime: `pandas[excel]`, `rich`, `numpy`, `scikit-learn`
- Dev: `pytest`, `pytest-cov`, `ruff`, `docformatter`

## Architecture

### `src/functions`

- `generate_id.py`: UUID-based ID generation used by all model dataclasses.
- `configure_logging.py`: application logging setup (env-driven log level, console handler).

### `src/cli`

- `cli.py` initializes config/app state and launches the menu system.
- `menu/` contains the reusable menu framework (`MenuBuilder`, `MenuHandler`, `MenuItem`).
- `handlers/config_handlers.py` shows loaded config/reference summaries and supports reload.
- `handlers/simulate_handlers.py` provides:
  - interactive hierarchy browsing (`Installation -> Facility -> System -> WorkOrder`)
  - quick generation stats
  - guided dataset export wizard
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

- `settings.py`: typed settings groups + reference collections in `MIDASSettings`
- `loader.py`: Excel loader/parsers for config, reference data, and distributions
- `distributions.py`: distribution system -- `ProbabilitySegment`/`ProbabilityDistribution` (weighted sampling), `EventRateDistribution` with `NormalCurve`, `BathtubCurve`, and `PiecewiseCurve` implementations, plus `DistributionContext` (age, life expectancy, CI)
- `app_state.py`: runtime singleton state (`get_app_state`, reload handling)
- `display.py`: Rich-based display helpers (`create_facility_types_table`, `create_system_types_table`, `create_installation_locations_table`, `create_config_values_panel`)
- `reference_data.py`: `FacilityType`, `SystemType`, `InstallationLocation`, `WorkOrderText`

### `src/simulation`

- `generator.py`: public facade (`DataGenerator`)
- `distributions.py`: re-export layer (canonical logic lives in `src/config/distributions.py`)
- `modules/base.py`: marker base class for simulation modules
- `generation_result.py`: typed `GenerationResult` contract with:
  - `installations`
  - `facilities`
  - `systems`
  - `work_orders`
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

## Configuration

All runtime behavior is driven by `src/config/midas_config_values.xlsx`.

Important configurable groups:

- simulation ranges (facility counts, max ages, dependency settings)
- degradation thresholds
- output naming (CSV separator + Excel sheet names)
- distributions:
  - condition index
  - age
  - grade
  - work-order count/status/priority

Defaults in `settings.py` are used if values are absent or invalid during load.

## Export Features

- Output formats: `csv`, `xlsx`
- Layouts:
  - `normalized`: separate tables/sheets
  - `denormalized`: flattened table
- Work orders are included in both layouts.
- Optional facility/system time-series data.
- Optional metadata output.

## Example Usage

```python
from pathlib import Path
from src.config import MIDASSettings
from src.simulation import DataExporter, DataGenerator

settings = MIDASSettings.from_excel(Path("src/config/midas_config_values.xlsx"))
generator = DataGenerator(settings=settings, seed=42)

result = generator.generate_installation()
print(len(result.installations), len(result.facilities), len(result.systems), len(result.work_orders))

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

## Tests

- `tests/conftest.py`: shared fixtures
- `tests/integration/test_config_loading_integration.py`: config loading from Excel
- `tests/integration/test_generation_and_export_integration.py`: end-to-end generation and export

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```
