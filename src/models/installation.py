from dataclasses import dataclass, field

from ..functions import generate_id


@dataclass
class Installation:
    """An installation containing multiple facilities.

    Top level of the domain hierarchy.
    """

    id: str = field(default_factory=generate_id)
    title: str = ""

    # Child references (IDs only)
    facility_ids: list[str] = field(default_factory=list)

    # Computed/aggregate values (set by services)
    condition_index: float | None = None
