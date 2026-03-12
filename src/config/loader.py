"""Configuration loader for Excel-based settings.

Loads reference data (facility types, system types) and settings
from the midas_config_values.xlsx file.
"""

from __future__ import annotations

import json
import logging
import random
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from pandas import ExcelFile

from .reference_data import FacilityType, InstallationLocation, SystemType

if TYPE_CHECKING:
    from .settings import (
        DegradationSettings,
        MIDASSettings,
        OutputSettings,
        SimulationDistributions,
        SimulationSettings,
    )

logger = logging.getLogger(__name__)


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    """Find a column name from a list of possible candidates.

    Performs case-insensitive matching and handles whitespace variations.

    Args:
        columns: Available column names in the DataFrame.
        candidates: List of possible column names to look for (in order of preference).

    Returns:
        The matching column name from columns, or None if not found.

    """
    # Normalize column names for comparison
    normalized_columns = {col.lower().replace(" ", "").replace("_", ""): col for col in columns}

    for candidate in candidates:
        normalized_candidate = candidate.lower().replace(" ", "").replace("_", "")
        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]

    return None


def _is_numeric(value: str) -> bool:
    """Check if a string can be converted to a number.

    Handles integers, floats, and numbers with leading/trailing whitespace.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""

    pass


def load_settings_from_excel(path: Path) -> MIDASSettings:
    """Load MIDAS settings from Excel configuration file.

    Args:
        path: Path to the Excel configuration file.

    Returns:
        Configured MIDASSettings instance.

    Raises:
        ConfigLoadError: If the file cannot be loaded or is invalid.

    """
    if not path.exists():
        raise ConfigLoadError(f"Configuration file not found: {path}")

    try:
        excel_file = ExcelFile(path)
    except (OSError, ValueError) as e:
        raise ConfigLoadError(f"Configuration load error: failed to open workbook at '{path}' ({e})") from e

    # Import settings models locally to avoid module import cycles.
    from .settings import MIDASSettings

    # Load reference data
    facility_types = _load_facility_types(excel_file)
    system_types = _load_system_types(excel_file)
    locations = _load_install_locations(excel_file)
    # Load settings from Config sheet (if present)
    degradation, simulation, output, config_dict = _load_config_values(excel_file)

    # Load distributions from config (falls back to defaults if not specified)
    distributions = _load_distributions(config_dict)

    # Eagerly load work-order text so generation never re-reads the workbook.
    wo_text_cache = _load_work_order_text_cache(excel_file)

    return MIDASSettings(
        degradation=degradation,
        simulation=simulation,
        output=output,
        distributions=distributions,
        facility_types=facility_types,
        system_types=system_types,
        installation_locations=locations,
        config_workbook_path=path,
        work_order_text_cache=wo_text_cache,
    )


def _load_facility_types(excel_file: ExcelFile) -> dict[int, FacilityType]:
    """Load facility types from Facilities sheet."""
    if "Facilities" not in excel_file.sheet_names:
        logger.warning("No 'Facilities' sheet found in config file")
        return {}

    df = pd.read_excel(excel_file, sheet_name="Facilities")
    facility_types = {}

    for _, row in df.iterrows():
        try:
            key = int(row.get("Key", 0))
            if pd.isna(key) or key == 0:
                continue

            facility_type = FacilityType(
                key=key,
                title=str(row.get("Title", "")).strip(),
                life_expectancy=int(row.get("Life Expectancy", 50)),
                mission_criticality=int(row.get("Mission Criticality", 1)) if not pd.isna(row.get("Mission Criticality")) else 1,
            )
            facility_types[key] = facility_type
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse facility type row: {e}")
            continue

    logger.info(f"Loaded {len(facility_types)} facility types")
    return facility_types


def _load_system_types(excel_file: ExcelFile) -> dict[int, SystemType]:
    """Load system types from Systems sheet."""
    if "Systems" not in excel_file.sheet_names:
        logger.warning("No 'Systems' sheet found in config file")
        return {}

    df = pd.read_excel(excel_file, sheet_name="Systems")
    system_types = {}

    # Find the facility keys column (handle various naming conventions)
    facility_keys_column = _find_column(
        df.columns, ["Facility Key(s)", "Facility Keys", "FacilityKeys", "Facility_Keys", "facility_keys"]
    )

    if not facility_keys_column:
        logger.warning(
            f"No 'Facility Key(s)' column found in Systems sheet. "
            f"Available columns: {list(df.columns)}. "
            f"System types will have empty facility_keys."
        )

    for _, row in df.iterrows():
        try:
            key = int(row.get("Key", 0))
            if pd.isna(key) or key == 0:
                continue

            # Parse facility keys (comma-separated or single value)
            facility_keys_raw = row.get(facility_keys_column, "") if facility_keys_column else ""
            if pd.isna(facility_keys_raw):
                facility_keys = ()
            elif isinstance(facility_keys_raw, (int, float)):
                facility_keys = (int(facility_keys_raw),)
            else:
                # Parse comma-separated string (handle both int and float formats)
                facility_keys = tuple(
                    int(float(k.strip())) for k in str(facility_keys_raw).split(",") if k.strip() and _is_numeric(k.strip())
                )

            system_type = SystemType(
                key=key,
                title=str(row.get("Title", "")).strip(),
                life_expectancy=int(row.get("Life Expectancy", 30)),
                facility_keys=facility_keys,
            )
            system_types[key] = system_type
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse system type row: {e}")
            continue

    logger.info(f"Loaded {len(system_types)} system types")
    return system_types


def _load_install_locations(excel_file: ExcelFile) -> list[InstallationLocation]:
    """Load installation location reference data."""
    if "Installation Locations" not in excel_file.sheet_names:
        logger.warning("No 'Installations Locations' sheet found in config file")
        return []

    df = pd.read_excel(excel_file, sheet_name="Installation Locations")
    locations = []

    for _, row in df.iterrows():
        try:
            title = row.get("Title", "")
            location = row.get("Location", "")
            region = row.get("Region", "")
            coordinates = row.get("Coordinates", "")

            locations.append(InstallationLocation(title=title, location=location, region=region, coordinates=coordinates))
        except (TypeError, ValueError) as e:
            logger.warning(f"Installation location parse error: invalid row data ({e})")
    logger.info(f"Loaded {len(locations)} Installation Locations")
    return locations


def _is_matching_text_header(value: Any) -> bool:
    return isinstance(value, str) and "description" in value.strip().lower()


def _resolve_work_order_text_column_bounds(
    title_row: list[Any], second_header_row: list[Any], system_type: str | None
) -> tuple[int, int, int] | None:
    """Resolve the description/request/action column indices for a system block."""
    if not system_type:
        return None

    normalized = system_type.strip().lower()
    candidate_indices = [idx for idx, value in enumerate(title_row) if isinstance(value, str) and value.strip().lower() == normalized]
    if not candidate_indices:
        return None

    for idx in candidate_indices:
        for start in (idx - 1, idx, idx + 1):
            if start < 0 or start + 2 >= len(second_header_row):
                continue
            if _is_matching_text_header(second_header_row[start]):
                return (start, start + 1, start + 2)

    # Fallback for merged-title cells where the title appears centered.
    first = candidate_indices[0]
    if first + 2 < len(second_header_row):
        return (first, first + 1, first + 2)
    return None


def _load_work_order_text_cache(excel_file: ExcelFile) -> dict[str, list[tuple[str, str, str]]]:
    """Eagerly load all work-order text triplets grouped by system type.

    Returns a dict mapping **lowercased** system-type title to a list of
    ``(description, requested_action, action_taken)`` triplets.  A special
    ``_fallback`` key collects the first valid triplet block for types that
    cannot be resolved.
    """
    if "Work Order Text" not in excel_file.sheet_names:
        return {}

    try:
        header_df = pd.read_excel(excel_file, sheet_name="Work Order Text", header=None, nrows=2)
    except Exception as exc:
        logger.warning(f"Failed loading Work Order Text headers: {exc}")
        return {}

    if header_df.empty or len(header_df.index) < 2:
        return {}

    title_row = header_df.iloc[0].tolist()
    second_header_row = header_df.iloc[1].tolist()

    try:
        body_df = pd.read_excel(excel_file, sheet_name="Work Order Text", header=None, skiprows=2)
    except Exception as exc:
        logger.warning(f"Failed loading Work Order Text body: {exc}")
        return {}

    if body_df.empty:
        return {}

    # Discover every (system_type_title -> column triplet) mapping.
    triplet_map: dict[str, tuple[int, int, int]] = {}
    fallback_triplet: tuple[int, int, int] | None = None

    seen_titles: set[str] = set()
    for idx, cell in enumerate(title_row):
        if not isinstance(cell, str) or not cell.strip():
            continue
        norm = cell.strip().lower()
        if norm in seen_titles:
            continue
        bounds = _resolve_work_order_text_column_bounds(title_row, second_header_row, cell.strip())
        if bounds is not None:
            triplet_map[norm] = bounds
            seen_titles.add(norm)

    # Build a fallback from the first description header found.
    if not triplet_map:
        for start in range(len(second_header_row) - 2):
            if _is_matching_text_header(second_header_row[start]):
                fallback_triplet = (start, start + 1, start + 2)
                break
    else:
        fallback_triplet = next(iter(triplet_map.values()))

    def _extract_rows(cols: tuple[int, int, int]) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        for _, row in body_df.iterrows():
            vals: list[str] = []
            for ci in cols:
                if ci < len(row):
                    v = row.iloc[ci]
                    vals.append(str(v).strip() if isinstance(v, str) and v.strip() else "example text")
                else:
                    vals.append("example text")
            while len(vals) < 3:
                vals.append("example text")
            rows.append((vals[0], vals[1], vals[2]))
        return rows

    cache: dict[str, list[tuple[str, str, str]]] = {}
    for title_key, cols in triplet_map.items():
        extracted = _extract_rows(cols)
        if extracted:
            cache[title_key] = extracted

    if fallback_triplet is not None:
        extracted = _extract_rows(fallback_triplet)
        if extracted:
            cache.setdefault("_fallback", extracted)

    logger.info(f"Loaded work-order text cache with {len(cache)} system-type groups")
    return cache


def sample_work_order_text_for_system(workbook_path: Path, system_type: str | None) -> tuple[str, str, str] | None:
    """Sample one text triplet for a given system type from the workbook on-demand.

    .. deprecated::
        Prefer the cached path via ``MIDASSettings.sample_work_order_text``
        which avoids re-reading the workbook on every call.
    """
    if not workbook_path.exists():
        return None

    try:
        header_df = pd.read_excel(workbook_path, sheet_name="Work Order Text", header=None, nrows=2)
    except Exception as exc:
        logger.warning(f"Failed loading Work Order Text headers from '{workbook_path}': {exc}")
        return None

    if header_df.empty or len(header_df.index) < 2:
        return None

    title_row = header_df.iloc[0].tolist()
    second_header_row = header_df.iloc[1].tolist()
    column_bounds = _resolve_work_order_text_column_bounds(title_row, second_header_row, system_type)
    if column_bounds is None:
        for start in range(len(second_header_row) - 2):
            if _is_matching_text_header(second_header_row[start]):
                column_bounds = (start, start + 1, start + 2)
                break
    if column_bounds is None:
        return None

    desc_col, req_col, act_col = column_bounds
    usecols = [desc_col, req_col, act_col]
    try:
        body_df = pd.read_excel(workbook_path, sheet_name="Work Order Text", header=None, skiprows=2, usecols=usecols)
    except Exception as exc:
        logger.warning(f"Failed loading Work Order Text rows from '{workbook_path}': {exc}")
        return None

    if body_df.empty:
        return ("example text", "example text", "example text")

    sampled_row = body_df.iloc[random.randrange(len(body_df.index))]
    values: list[str] = []
    for value in sampled_row.tolist():
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        else:
            values.append("example text")
    while len(values) < 3:
        values.append("example text")

    return (values[0], values[1], values[2])


# Mapping from human-readable Excel parameter names to internal setting keys
PARAMETER_KEY_MAP: dict[str, str] = {
    # Degradation settings
    "condition index degraded threshold": "condition_index_degraded_threshold",
    "resiliency grade threshold": "resiliency_grade_threshold",
    "initial condition index": "initial_condition_index",
    "maximum time series years history": "max_time_series_years",
    # Simulation settings
    "facilities per installation": "facilities_per_installation",
    "dependency chain group range": "dependency_chain_group_range",
    "maximum system age": "maximum_system_age",
    "maximum facility age": "maximum_facility_age",
    "facility condition randomly degrades chance": "facility_condition_randomly_degrades_chance",
    # Output settings
    "output excel sheet main name": "excel_sheet_main",
    "output excel sheet facility ts name": "excel_sheet_facility_ts",
    "output excel sheet system ts name": "excel_sheet_system_ts",
    "output excel sheet work orders name": "excel_sheet_work_orders",
    "output excel sheet metadata name": "excel_sheet_metadata",
    "outputed metadata file suffix": "metadata_file_suffix",
    "outputs csv table separator": "csv_table_separator",
    # Distribution settings
    "simulated condition index distribution": "condition_index_distribution",
    "simulated age distribution": "age_distribution",
    "simulated grade distribution": "grade_distribution",
    "simulated work order count distribution": "work_order_count_distribution",
    "simulated work order status distribution": "work_order_status_distribution",
    "simulated work order priority distribution": "work_order_priority_distribution",
    "simulated work order requesting organization distribution": "work_order_requesting_organization_distribution",
}


def _normalize_parameter_key(param: str) -> str:
    """Normalize a parameter name to a lookup key.

    Handles both human-readable names (from Excel Parameter column) and
    internal snake_case names (from Key/Setting column).
    """
    normalized = str(param).strip().lower()
    # If it's a human-readable name, map it to the internal key
    if normalized in PARAMETER_KEY_MAP:
        return PARAMETER_KEY_MAP[normalized]
    # Otherwise assume it's already a valid internal key
    return normalized.replace(" ", "_")


def _load_config_values(
    excel_file: ExcelFile,
) -> tuple[DegradationSettings, SimulationSettings, OutputSettings, dict[str, Any]]:
    """Load configuration values from Config sheet.

    Returns:
        Tuple of (DegradationSettings, SimulationSettings, OutputSettings, raw_config_dict)
        The raw config dict is returned for additional parsing (e.g., distributions).

    """
    from .settings import DegradationSettings, OutputSettings, SimulationSettings

    # Return defaults if no Config sheet
    if "Config" not in excel_file.sheet_names:
        return DegradationSettings(), SimulationSettings(), OutputSettings(), {}

    df = pd.read_excel(excel_file, sheet_name="Config")

    # Build a key-value dict from the sheet
    # Support multiple possible column names: Parameter, Key, Setting
    config_dict: dict[str, Any] = {}
    for _, row in df.iterrows():
        # Try different column names for the parameter identifier
        param = row.get("Parameter") or row.get("Key") or row.get("Setting")
        # Use Value column if present, otherwise fall back to Default
        value = row.get("Value")
        if pd.isna(value):
            value = row.get("Default")

        if not pd.isna(param) and not pd.isna(value):
            key = _normalize_parameter_key(param)
            config_dict[key] = value

    # Parse degradation settings
    degradation = DegradationSettings(
        condition_index_degraded_threshold=float(config_dict.get("condition_index_degraded_threshold", 25.0)),
        resiliency_grade_threshold=int(config_dict.get("resiliency_grade_threshold", 70)),
        initial_condition_index=float(config_dict.get("initial_condition_index", 99.99)),
        max_time_series_years=int(config_dict.get("max_time_series_years", 10)),
    )

    # Parse simulation settings
    facilities_range = _parse_range(config_dict.get("facilities_per_installation", "8-14"))
    dep_chain_range = _parse_range(config_dict.get("dependency_chain_group_range", "1-3"))

    simulation = SimulationSettings(
        facilities_per_installation=facilities_range,
        dependency_chain_group_range=dep_chain_range,
        maximum_system_age=int(config_dict.get("maximum_system_age", 80)),
        maximum_facility_age=int(config_dict.get("maximum_facility_age", 80)),
        facility_condition_randomly_degrades_chance=int(config_dict.get("facility_condition_randomly_degrades_chance", 35)),
    )

    # Parse output settings
    output = OutputSettings(
        excel_sheet_main=str(config_dict.get("excel_sheet_main", "Main Data")).strip(),
        excel_sheet_facility_ts=str(config_dict.get("excel_sheet_facility_ts", "Facility Time Series")).strip(),
        excel_sheet_system_ts=str(config_dict.get("excel_sheet_system_ts", "System Time Series")).strip(),
        excel_sheet_work_orders=str(config_dict.get("excel_sheet_work_orders", "Work Orders")).strip(),
        excel_sheet_metadata=str(config_dict.get("excel_sheet_metadata", "_metadata")).strip(),
        metadata_file_suffix=str(config_dict.get("metadata_file_suffix", "_metadata.json")).strip(),
        csv_table_separator=str(config_dict.get("csv_table_separator", "_")).strip(),
    )

    return degradation, simulation, output, config_dict


def _parse_distribution_string(value: str) -> list[tuple[int, str]] | None:
    r"""Parse a distribution string from Excel into (percentage, value_range) tuples.

    Supports formats like:
        - "1: (7: 1-50)\\n2: (88: 50-85)\\n3: (5: 85-100)"
        - "1: (50, 20-40)\\n2: (20, 10-20)"
        - "G1: 52\\nG2: 32\\nG3: 12\\nG4: 4"

    Returns:
        List of (percentage, value_string) tuples, or None if parsing fails.

    """
    if not value or pd.isna(value):
        return None

    value_str = str(value).strip()
    segments: list[tuple[int, str]] = []

    # Split by newline or numbered segments
    lines = re.split(r"\n|(?=\d+:\s*\()", value_str)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Pattern 1: "N: (percentage, range)" or "N: (percentage: range)"
        # e.g., "1: (7: 1-50)" or "1: (50, 20-40)"
        match = re.match(r"(?:\d+:\s*)?\(?\s*(\d+)\s*[,:]\s*([\d\-]+)\s*\)?", line)
        if match:
            percentage = int(match.group(1))
            value_range = match.group(2).strip()
            segments.append((percentage, value_range))
            continue

        # Pattern 2: "GN: percentage" for grade distributions
        # e.g., "G1: 52"
        match = re.match(r"G(\d+)\s*:\s*(\d+)", line)
        if match:
            grade = match.group(1)
            percentage = int(match.group(2))
            segments.append((percentage, grade))
            continue

    return segments if segments else None


def _parse_weighted_category_distribution(value: str) -> list[tuple[int, str]] | None:
    r"""Parse weighted categorical lines into (percentage, value) tuples.

    Supported examples:
    - "Completed: 52\\nIn Progress: 26"
    - "52: Completed\\n26: In Progress"
    """
    if not value or pd.isna(value):
        return None

    value_str = str(value).strip()
    if not value_str:
        return None

    # Normalize escaped newline literals (\\n) to real newlines so
    # splitlines() can separate entries regardless of how Excel stored them.
    value_str = value_str.replace("\\n", "\n")

    segments: list[tuple[int, str]] = []
    for line in value_str.splitlines():
        item = line.strip()
        if not item:
            continue

        # Format: Label: 40
        match = re.match(r"(.+?)\s*:\s*(\d+)\s*$", item)
        if match:
            label = match.group(1).strip()
            pct = int(match.group(2))
            segments.append((pct, label))
            continue

        # Format: 40: Label
        match = re.match(r"(\d+)\s*:\s*(.+?)\s*$", item)
        if match:
            pct = int(match.group(1))
            label = match.group(2).strip()
            segments.append((pct, label))

    return segments if segments else None


def _parse_distribution_spec(value: Any) -> dict[str, Any] | None:
    """Parse JSON distribution spec from config cell."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or not text.startswith("{"):
        return None
    try:
        spec = json.loads(text)
        return spec if isinstance(spec, dict) else None
    except json.JSONDecodeError:
        return None


def _load_distributions(config_dict: dict[str, Any]) -> SimulationDistributions:
    """Load probability distributions from config dictionary.

    Parses distribution strings from the config and creates ProbabilityDistribution
    objects. Falls back to defaults if parsing fails or values are not provided.
    """
    from .distributions import (
        BaseDistribution,
        ProbabilityDistribution,
        ProbabilitySegment,
        create_distribution_from_spec,
    )
    from .settings import SimulationDistributions

    condition_index = None
    age = None
    grade = None
    work_order_count: BaseDistribution | None = None
    work_order_status = None
    work_order_priority = None
    work_order_requesting_organization = None

    # Parse condition index distribution
    ci_str = config_dict.get("condition_index_distribution")
    if ci_str:
        segments = _parse_distribution_string(ci_str)
        if segments:
            try:
                condition_index = ProbabilityDistribution([ProbabilitySegment(pct, val) for pct, val in segments])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse condition index distribution: {e}")

    # Parse age distribution
    age_str = config_dict.get("age_distribution")
    if age_str:
        segments = _parse_distribution_string(age_str)
        if segments:
            try:
                age = ProbabilityDistribution([ProbabilitySegment(pct, val) for pct, val in segments])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse age distribution: {e}")

    # Parse grade distribution
    grade_str = config_dict.get("grade_distribution")
    if grade_str:
        segments = _parse_distribution_string(grade_str)
        if segments:
            try:
                grade = ProbabilityDistribution([ProbabilitySegment(pct, val) for pct, val in segments])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse grade distribution: {e}")

    # Parse work-order count distribution (curve spec preferred, segment fallback)
    wo_count_config = config_dict.get("work_order_count_distribution")
    if wo_count_config:
        spec = _parse_distribution_spec(wo_count_config)
        if spec:
            try:
                work_order_count = create_distribution_from_spec(spec)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse work-order count spec: {e}")
        else:
            segments = _parse_distribution_string(str(wo_count_config))
            if segments:
                try:
                    work_order_count = ProbabilityDistribution([ProbabilitySegment(pct, val) for pct, val in segments])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse work-order count distribution: {e}")

    # Parse work-order status distribution
    wo_status_config = config_dict.get("work_order_status_distribution")
    if wo_status_config:
        spec = _parse_distribution_spec(wo_status_config)
        if spec:
            try:
                maybe_dist = create_distribution_from_spec(spec)
                if isinstance(maybe_dist, ProbabilityDistribution):
                    work_order_status = maybe_dist
                else:
                    logger.warning("work_order_status_distribution must resolve to segments")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse work-order status spec: {e}")
        else:
            segments = _parse_weighted_category_distribution(str(wo_status_config))
            if segments:
                try:
                    work_order_status = ProbabilityDistribution([ProbabilitySegment(pct, val) for pct, val in segments])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse work-order status distribution: {e}")

    # Parse work-order priority distribution
    wo_priority_config = config_dict.get("work_order_priority_distribution")
    if wo_priority_config:
        spec = _parse_distribution_spec(wo_priority_config)
        if spec:
            try:
                maybe_dist = create_distribution_from_spec(spec)
                if isinstance(maybe_dist, ProbabilityDistribution):
                    work_order_priority = maybe_dist
                else:
                    logger.warning("work_order_priority_distribution must resolve to segments")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse work-order priority spec: {e}")
        else:
            segments = _parse_weighted_category_distribution(str(wo_priority_config))
            if segments:
                try:
                    work_order_priority = ProbabilityDistribution([ProbabilitySegment(pct, val) for pct, val in segments])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse work-order priority distribution: {e}")

    # Parse work-order requesting organization distribution
    wo_requesting_org_config = config_dict.get("work_order_requesting_organization_distribution")
    if wo_requesting_org_config:
        spec = _parse_distribution_spec(wo_requesting_org_config)
        if spec:
            try:
                maybe_dist = create_distribution_from_spec(spec)
                if isinstance(maybe_dist, ProbabilityDistribution):
                    work_order_requesting_organization = maybe_dist
                else:
                    logger.warning("work_order_requesting_organization_distribution must resolve to segments")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse work-order requesting organization spec: {e}")
        else:
            segments = _parse_weighted_category_distribution(str(wo_requesting_org_config))
            if segments:
                try:
                    work_order_requesting_organization = ProbabilityDistribution(
                        [ProbabilitySegment(pct, val) for pct, val in segments]
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse work-order requesting organization distribution: {e}")

    # Create distributions - None values will use defaults from __post_init__
    return SimulationDistributions(
        condition_index=condition_index,
        age=age,
        grade=grade,
        work_order_count=work_order_count,
        work_order_status=work_order_status,
        work_order_priority=work_order_priority,
        work_order_requesting_organization=work_order_requesting_organization,
    )


def _parse_range(value: str | int | float) -> tuple[int, int]:
    """Parse a range value like '8-14' or single value like '10'."""
    if isinstance(value, (int, float)):
        v = int(value)
        return (v, v)

    value_str = str(value).strip()
    if "-" in value_str:
        parts = value_str.split("-")
        if len(parts) == 2:
            try:
                return (int(parts[0].strip()), int(parts[1].strip()))
            except ValueError:
                pass
    try:
        v = int(value_str)
        return (v, v)
    except ValueError:
        return (8, 14)  # Default
