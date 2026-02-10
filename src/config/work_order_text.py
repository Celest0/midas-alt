"""
Work order text selector.

Selects appropriate work-order text blocks from Excel configuration
based on facility/system parameters. Does not store all data in memory.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from .settings import MIDASSettings


class WorkOrderTextNotFound(Exception):
    """Raised when no matching work-order text is found."""
    pass


def select_work_order_text(
    *,
    settings: MIDASSettings,
    facility_type_key: Optional[int],
    system_type_key: Optional[int],
    condition_index: float,
    age: int,
    mission_criticality: int,
    resiliency_grade: int,
    remaining_service_life: int,
    config_path: Optional[Path] = None,
) -> dict[str, str]:
    """
    Select a work-order text block based on input parameters.

    Returns:
        {
            "problem_description": str,
            "requested_action": str,
            "actions_taken": str,
        }
    """

    path = config_path or settings.default_config_path()

    df = pd.read_excel(path, sheet_name="WorkOrderText")

    # Apply filters incrementally (cheap + readable)
    if facility_type_key is not None:
        df = df[
            (df["FacilityTypeKey"].isna()) |
            (df["FacilityTypeKey"] == facility_type_key)
        ]

    if system_type_key is not None:
        df = df[
            (df["SystemTypeKey"].isna()) |
            (df["SystemTypeKey"] == system_type_key)
        ]

    df = df[
        (df["MinConditionIndex"] <= condition_index) &
        (df["MaxConditionIndex"] >= condition_index) &
        (df["MinAge"] <= age) &
        (df["MaxAge"] >= age) &
        (df["MissionCriticality"] <= mission_criticality) &
        (df["ResiliencyGrade"] <= resiliency_grade) &
        (df["RemainingServiceLifeMin"] <= remaining_service_life) &
        (df["RemainingServiceLifeMax"] >= remaining_service_life)
    ]

    if df.empty:
        raise WorkOrderTextNotFound(
            "No matching work-order text found for provided parameters."
        )

    # Pick first match (deterministic)
    row = df.iloc[0]

    return {
        "problem_description": str(row["ProblemDescription"]).strip(),
        "requested_action": str(row["RequestedAction"]).strip(),
        "actions_taken": str(row["ActionsTaken"]).strip(),
    }
