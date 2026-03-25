"""Enumerations for work-order priority, trade skill, and status.

- WorkOrderPriority: Priority levels for work orders (Emergency, Urgent, Routine, Maintenance).
- WorkOrderTradeSkill: Skilled trades required to perform work orders (HVAC, Electrical, Structural, Fire Protection).
- WorkOrderStatus: Workflow states for work orders (Submitted, Approved, In Progress, Completed).

Work-order values are aligned to HQ SPOC/S4W guidance:
https://static.e-publishing.af.mil/production/1/spoc/publication/spoci21-108/spoci21-108.pdf

The key classification attributes used in work order tracking and processing across the application.
"""

from enum import Enum


class WO_Priority(Enum):
    """Priority categories for work-order urgency."""

    EMERGENCY = "Emergency"
    URGENT = "Urgent"
    ROUTINE = "Routine"
    MAINTENANCE = "Maintenance"


class WO_TradeSkill(Enum):
    """Skilled trades associated with work-order execution."""

    HVAC = "HVAC"
    ELECTRICAL = "Electrical"
    STRUCTURAL = "Structural"
    FIRE_PROTECTION = "Fire Protection"
    PLUMBING = "Plumbing"


class WO_Status(Enum):
    """Lifecycle states for work-order processing."""

    SUBMITTED = "Submitted"
    APPROVED = "Approved"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
