# MIDAS

MIDAS (**M**ission **I**nfrastructure **D**egradation **A**nalysis **S**imulation) is a Python application for simulating and managing installation, facility, and system data. It provides a menu-based CLI interface for generating simulated data, viewing configurations, and training ML models to predict infrastructure degradation.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Architecture Overview](#architecture-overview)
- [Configuration System](#configuration-system)
- [CLI System](#cli-system)
- [Simulation Engine](#simulation-engine)
- [API Patterns & Conventions](#api-patterns--conventions)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)

---

## Prerequisites

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package installer and resolver

### Installing uv

If you don't have `uv` installed, follow the [official installation guide](https://github.com/astral-sh/uv?tab=readme-ov-file#installation):

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd midas-alt
```

### 2. Set Up the Development Environment

```bash
# Create virtual environment
uv venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies (uv handles this automatically when using uv run)
# Dependencies are managed in pyproject.toml
```

### 3. Run the Application

```bash
uv run python main.py
```

The application will:
- Load configuration from `src/config/midas_config_values.xlsx`
- Display a welcome message
- Present an interactive menu system for navigation

---

## Architecture Overview

MIDAS follows a clean, modular architecture with clear separation of concerns:

```
┌──────────────────────────────────────────────┐
│                  CLI Layer                   │
│  (menus, handlers, display utilities)        │
├──────────────────────────────────────────────┤
│                Service Layer                 │
│  ┌─────────────────┐  ┌─────────────────┐    │
│  │   Simulation    │  │   Prediction    │    │
│  │    Engine       │  │    Pipeline     │    │
│  └────────┬────────┘  └────────┬────────┘    │
│           │                    │             │
│  ┌────────▼────────────────────▼────────┐    │
│  │          Configuration               │    │
│  │    (Settings, Reference Data)        │    │
│  └────────────────┬─────────────────────┘    │
├───────────────────┼──────────────────────────┤
│                   ▼                          │
│              Domain Layer                    │
│  (Entities: Installation, Facility, System)  │
└──────────────────────────────────────────────┘
```
## Core Models and Structure

### Installation

Top-level entity representing a physical installation/site.

```python
@dataclass
class Installation:
    id: str                           # UUID
    title: str                        # Human-readable name
    facility_ids: list[str]           # Child facility references
    condition_index: float | None     # Aggregate CI from facilities
```

### Facility

Mid-level entity representing a building or facility within an installation.

```python
@dataclass
class Facility:
    id: str
    facility_type_key: int            # Reference to FacilityType
    year_constructed: int
    dependency_chain: DependencyChain # Position in dependency hierarchy
    resiliency_grade: UFCGrade        # UFC 4-141-03 grade (G1-G4)
    condition_index: float            # Aggregate from systems
    system_ids: list[str]             # Child system references
```

### System

Lowest-level entity representing a specific system within a facility.

```python
@dataclass
class System:
    id: str
    system_type_key: int              # Reference to SystemType
    year_constructed: int
    condition_index: float            # Directly measured/simulated
    facility_id: str                  # Parent facility reference
```

### Dependency Chains

Facilities are organized into dependency hierarchies using a flexible letter-based vertical position system:

- **Vertical position**: A single letter `A`–`Z`, where `A` is the top of the hierarchy and each subsequent letter represents a deeper dependency level.
- **Group IDs**: Any combination of digits `1`–`9`, each representing membership in one of 9 possible groups. Entities sharing a group ID within the same hierarchy are considered related.
- **Hierarchy rule**: An entity at a given position (e.g., `B`) depends on entities above it (e.g., `A`) that share at least one group ID.

Position format: `{vertical_position}{group_ids}` (e.g., `"A1"` = top-level, group 1; `"B23"` = second level, groups 2 and 3)

### UFC Resiliency Grades

Based on UFC 4-141-03 standards:

| Grade | Redundancy Level                                         |
|-------|----------------------------------------------------------|
| G1    | No redundancy, maintenance causes downtime               |
| G2    | Some component redundancy, single path to critical loads |
| G3    | Concurrently maintainable, N+1 redundancy                |
| G4    | Fault-tolerant, 2N redundancy with automatic failover    |

---

## Configuration System

### MIDASSettings

The central configuration container, loaded once at startup:

```python
@dataclass
class MIDASSettings:
    degradation: DegradationSettings      # CI thresholds, initial values
    simulation: SimulationSettings        # Generation parameters
    output: OutputSettings                # Export configuration
    distributions: SimulationDistributions # Probability distributions
    
    facility_types: dict[int, FacilityType]  # Loaded from Excel
    system_types: dict[int, SystemType]      # Loaded from Excel
```

### Loading Configuration

```python
from src.config import MIDASSettings

# From Excel file (recommended)
settings = MIDASSettings.from_excel(Path("src/config/midas_config_values.xlsx"))

# With defaults (no reference data)
settings = MIDASSettings.with_defaults()
```

### Reference Data Types

**FacilityType**: Defines facility categories with life expectancy and mission criticality.

**SystemType**: Defines system categories with life expectancy and which facility types they belong to.

### Application State

The `ApplicationState` class manages runtime state for the CLI:

```python
from src.config import get_app_state, set_app_state

# Get current state (initializes if needed)
state = get_app_state()

# Access settings
settings = state.settings

# Check initialization status
if state.initialized_successfully:
    print(f"Loaded {len(settings.facility_types)} facility types")
```

---

## CLI System

### Menu Architecture

The CLI uses a composable menu system built on Rich:

```
MenuBuilder ─builds─▶ MenuHandler ─uses─▶ MenuItem
     │                     │                  │
     ▼                     ▼                  ▼
 Fluent API           Run loop           Action callbacks
```

### Building Menus

```python
from src.cli.menu import MenuBuilder

def get_my_menu():
    builder = MenuBuilder("My Menu")
    builder.add_item(
        label="Do Something",
        action=handle_do_something,
        description="Performs an important action",
    )
    builder.add_separator()
    builder.add_item(
        label="Exit",
        action=lambda: None,
        exit_menu=True,
    )
    return builder.build()
```

### MenuItem Options

| Option             | Type     | Description                      |
|--------------------|----------|----------------------------------|
| `label`            | str      | Display text for the item        |
| `action`           | Callable | Function to execute on selection |
| `exit_menu`        | bool     | Exit menu after action           |
| `enabled`          | bool     | Whether item is selectable       |
| `visible`          | bool     | Whether item is shown            |
| `separator_before` | bool     | Add visual separator before item |
| `description`      | str      | Help text shown inline           |

### Display Utilities

The `DisplayHelper` class provides consistent output formatting:

```python
from src.cli.utils import DisplayHelper, InputHelper

# Display panels
DisplayHelper.print_panel("Content here", title="My Panel")
DisplayHelper.print_success("Operation completed!")
DisplayHelper.print_error("Something went wrong")
DisplayHelper.print_warning("Be careful!")

# Input helpers
value = InputHelper.ask_number("Enter count", min_value=1, max_value=100)
confirmed = InputHelper.ask_yes_no("Proceed?", default=True)
choice = InputHelper.ask_choice("Select option", choices=["a", "b", "c"])
```

---

## Simulation Engine

### DataGenerator

Generates realistic simulated data with configurable distributions:

```python
from src.simulation import DataGenerator
from src.config import MIDASSettings

settings = MIDASSettings.from_excel(config_path)
generator = DataGenerator(settings=settings, seed=42)

# Generate single installation
installation, facilities, systems = generator.generate_installation()

# Generate multiple installations
installations, all_facilities, all_systems = generator.generate_installations(count=10)
```

### Probability Distributions

Simulation uses configurable probability segments:

```python
# Condition Index Distribution (default)
# 7% chance of CI 1-50 (poor)
# 88% chance of CI 50-85 (fair to good)
# 5% chance of CI 85-100 (excellent)

# Age Distribution (default)
# 10% chance of 0-9 years
# 20% chance of 10-20 years
# 50% chance of 20-40 years
# 20% chance of 41-80 years
```

### Data Export

Export generated data to multiple formats:

```python
from src.simulation import DataExporter

exporter = DataExporter(
    file_name="my_dataset",
    output_format="csv",          # or "json", "xlsx"
    output_directory="./output",
    layout="normalized",          # or "denormalized"
    include_time_series=False,
    generate_metadata=True,
    settings=settings,
)

# Generate and export in one call
file_path = exporter.generate_and_export(
    method="installations",       # or "facilities", "default"
    target_count=100,
)
```

### Output Formats

| Format | Description                                           |
|--------|-------------------------------------------------------|
| CSV    | Separate files for installations, facilities, systems |
| JSON   | Single file with nested structure                     |
| XLSX   | Excel workbook with multiple sheets                   |

### Output Layouts

| Layout         | Description                                                  |
|----------------|--------------------------------------------------------------|
| `normalized`   | Separate tables with foreign key relationships (recommended) |
| `denormalized` | Single flattened table with all data joined                  |

---

## API Patterns & Conventions

### Dependency Injection

Services receive configuration via constructor injection:

```python
# Good: Explicit dependency injection
class DataGenerator:
    def __init__(self, settings: MIDASSettings):
        self.settings = settings

# Usage
settings = MIDASSettings.from_excel(path)
generator = DataGenerator(settings=settings)
```

### Immutable Configuration

Settings objects are frozen dataclasses:

```python
@dataclass(frozen=True)
class DegradationSettings:
    condition_index_degraded_threshold: float = 25.0
    # Cannot be modified after creation
```

### Builder Pattern

Complex objects use builder pattern for construction:

```python
menu = (MenuBuilder("My Menu")
    .add_item("Option 1", action1)
    .add_item("Option 2", action2)
    .add_separator()
    .add_item("Exit", exit_action, exit_menu=True)
    .build())
```

### Strategy Pattern

Exporters use strategy pattern for different formats:

```python
# Base formatter interface
class BaseFormatter(ABC):
    @abstractmethod
    def export(self, data) -> Path: ...

# Concrete implementations
class CSVFormatter(BaseFormatter): ...
class JSONFormatter(BaseFormatter): ...
class ExcelFormatter(BaseFormatter): ...
```

## Project Structure

```
midas-alt/
├── main.py                    # Application entry point
├── pyproject.toml             # Dependencies and tool configuration
├── README.md                  # This file
│
├── src/
│   ├── cli/                   # CLI layer
│   │   ├── cli.py             # Main CLI runner
│   │   ├── handlers/          # Command handlers
│   │   │   ├── config_handlers.py
│   │   │   ├── ml_handlers.py
│   │   │   └── simulate_handlers.py
│   │   ├── menu/              # Menu system
│   │   │   ├── menu_builder.py
│   │   │   ├── menu_config.py
│   │   │   ├── menu_factory.py
│   │   │   ├── menu_handler.py
│   │   │   └── menu_item.py
│   │   └── utils/             # CLI utilities
│   │       ├── display.py
│   │       ├── input.py
│   │       └── navigation.py
│   │
│   ├── config/                # Configuration system
│   │   ├── app_state.py       # Runtime state management
│   │   ├── loader.py          # Excel config loader
│   │   ├── reference_data.py  # FacilityType, SystemType
│   │   ├── settings.py        # MIDASSettings
│   │   └── midas_config_values.xlsx  # Configuration file
│   │
│   ├── domain/                # Domain entities
│   │   ├── entities.py        # Installation, Facility, System
│   │   └── enums.py           # UFCGrade, DependencyTier
│   │
│   ├── prediction/            # ML prediction module
│   │   ├── datasets.py        # TrainingDataGenerator, DatasetConfig
│   │   ├── features.py        # FeatureExtractor, DegradationFeatures
│   │   └── models/
│   │       ├── base.py        # DegradationModel ABC
│   │       └── regression.py  # SklearnRegressionModel
│   │
│   └── simulation/            # Data simulation
│       ├── distributions.py   # ProbabilityDistribution
│       ├── generator.py       # DataGenerator
│       └── export/
│           ├── config.py      # ExportConfig
│           ├── enums.py       # OutputFormat, OutputLayout
│           ├── exporter.py    # DataExporter
│           ├── transformers.py
│           └── formatters/
│               ├── base.py
│               ├── csv_formatter.py
│               ├── excel_formatter.py
│               └── json_formatter.py
│
├── examples/
│   └── ml_prediction_demo.py  # Standalone ML demo script
│
├── generated_data/            # Sample generated output
│   ├── generated_data_facilities.csv
│   ├── generated_data_installations.csv
│   ├── generated_data_metadata.json
│   └── generated_data_systems.csv
│
└── docs/                      # Additional documentation
```

---

## Development Workflow

### Running Tests

```bash
# Run all tests with coverage
uv run pytest

# Run tests in verbose mode
uv run pytest -v

# Run specific test file
uv run pytest tests/test_simulation.py
```

### Code Quality

```bash
# Check for linting errors
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Format docstrings (optional)
uv run docformatter --in-place --recursive .
```

### Configuration

The project uses `pyproject.toml` for all configuration:

- **Ruff**: Linting rules (pycodestyle, pyflakes, isort, etc.)
- **Pytest**: Test configuration with coverage

---

## Dependencies

| Package      | Version | Purpose                          |
|--------------|---------|----------------------------------|
| numpy        | ≥2.4.0  | Numerical computing              |
| pandas       | ≥2.3.3  | Data manipulation, Excel support |
| rich         | ≥13.7.0 | Terminal formatting              |
| scikit-learn | ≥1.6.0  | ML models and evaluation         |

### Development Dependencies

| Package      | Version  | Purpose                |
|--------------|----------|------------------------|
| pytest       | ≥9.0.2   | Testing framework      |
| pytest-cov   | ≥7.0.0   | Coverage reporting     |
| ruff         | ≥0.14.10 | Linting and formatting |
| docformatter | ≥1.7.0   | Docstring formatting   |

---
