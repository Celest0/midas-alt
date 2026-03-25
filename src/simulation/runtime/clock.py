"""Clock primitives for time-stepped simulation sessions."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class TickUnit(Enum):
    """Units supported by the simulation clock."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass(frozen=True)
class TickSize:
    """A discrete unit of time advanced on each simulation tick."""

    amount: int = 1
    unit: TickUnit = TickUnit.DAY

    def __post_init__(self) -> None:
        """Validate tick-size values."""
        if self.amount <= 0:
            raise ValueError("TickSize.amount must be greater than zero")

    @property
    def label(self) -> str:
        """Return a human-readable label for the tick size."""
        suffix = self.unit.value if self.amount == 1 else f"{self.unit.value}s"
        return f"{self.amount} {suffix}"

    def advance(self, value: date) -> date:
        """Advance a date by this tick size."""
        if self.unit == TickUnit.DAY:
            return value + timedelta(days=self.amount)
        if self.unit == TickUnit.WEEK:
            return value + timedelta(weeks=self.amount)
        if self.unit == TickUnit.MONTH:
            return _add_months(value, self.amount)
        return _add_months(value, self.amount * 12)

    @classmethod
    def presets(cls) -> list[TickSize]:
        """Return the default tick-size presets used by the CLI."""
        return [
            cls(amount=1, unit=TickUnit.DAY),
            cls(amount=1, unit=TickUnit.WEEK),
            cls(amount=1, unit=TickUnit.MONTH),
            cls(amount=1, unit=TickUnit.YEAR),
        ]


@dataclass
class SimulationClock:
    """Tracks the current simulated date and tick count."""

    current_date: date
    tick_size: TickSize = TickSize()
    tick_index: int = 0

    def advance(self) -> date:
        """Advance the clock by the configured tick size."""
        self.current_date = self.tick_size.advance(self.current_date)
        self.tick_index += 1
        return self.current_date

    def cycle_tick_size(self) -> TickSize:
        """Cycle through the default tick-size presets."""
        presets = TickSize.presets()
        try:
            current_index = presets.index(self.tick_size)
        except ValueError:
            current_index = -1
        self.tick_size = presets[(current_index + 1) % len(presets)]
        return self.tick_size

    def set_tick_size(self, tick_size: TickSize) -> None:
        """Set the active tick size."""
        self.tick_size = tick_size


def _add_months(value: date, months: int) -> date:
    """Advance a date by a number of months, clamping the day if needed."""
    total_months = (value.year * 12 + value.month - 1) + months
    year = total_months // 12
    month = (total_months % 12) + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
