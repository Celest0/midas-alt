"""This module defines enumerations related to the Work Order domain:

- WorkOrderPriority: Priority levels for work orders (Emergency, Urgent, Routine, Maintenance).
- WorkOrderTradeSkill: Skilled trades required to perform work orders (HVAC, Electrical, Structural, Fire Protection).
- WorkOrderStatus: Workflow states for work orders (Submitted, Approved, In Progress, Completed).

The key classification attributes used in work order tracking and processing across the application.
"""

from enum import Enum


class WorkOrderPriority(Enum):
    EMERGENCY = "Emergency"
    URGENT = "Urgent"
    ROUTINE = "Routine"
    MAINTENANCE = "Maintenance"


class WorkOrderTradeSkill(Enum):
    HVAC = "HVAC"
    ELECTRICAL = "Electrical"
    STRUCTURAL = "Structural"
    FIRE_PROTECTION = "Fire Protection"


class WorkOrderStatus(Enum):
    SUBMITTED = "Submitted"
    APPROVED = "Approved"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
