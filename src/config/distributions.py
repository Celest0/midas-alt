"""Probability distribution utilities for data simulation."""

import math
import random
import re
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class DistributionContext:
    """Optional runtime context used by lifecycle-aware distributions."""

    age_years: float | None = None
    life_expectancy_years: float | None = None
    condition_index: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_ratio(self) -> float | None:
        """Return normalized age ratio when possible."""
        if self.age_years is None or self.life_expectancy_years in (None, 0):
            return None
        return self.age_years / self.life_expectancy_years


class BaseDistribution(Protocol):
    """Protocol for reusable distributions."""

    def sample(self, context: DistributionContext | None = None) -> float | str:
        """Sample a value from the distribution."""


class ProbabilitySegment:
    """Represents a single segment in a probability distribution."""

    def __init__(self, percentage: int, value: str) -> None:
        """Initialize a weighted segment with percent and raw value."""
        if not (1 <= percentage <= 100):
            raise ValueError(f"Percentage must be between 1 and 100, got {percentage}")
        if value is None or str(value).strip() == "":
            raise ValueError("Value cannot be None or an empty string")

        self._percentage = percentage
        self._value = str(value)
        self._parsed_value: int | tuple[int, int] | None = None

    @property
    def percentage(self) -> float:
        """Return the segment weight as a 0-1 fraction."""
        return self._percentage / 100.0

    @percentage.setter
    def percentage(self, percent: int) -> None:
        if not (1 <= percent <= 100):
            raise ValueError(f"Percentage must be between 1 and 100, got {percent}")
        self._percentage = percent

    @property
    def value(self) -> str:
        """Return the raw configured segment value."""
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        if value is None or str(value).strip() == "":
            raise ValueError("Value cannot be None or an empty string")
        self._value = str(value)
        self._parsed_value = None

    @property
    def parsed_value(self) -> int | tuple[int, int] | None:
        """Return parsed integer/range form when possible."""
        if self._parsed_value is None:
            self._parsed_value = self._parse_value()
        return self._parsed_value

    def is_range_value(self) -> bool:
        """Return True when the segment represents a numeric range."""
        return isinstance(self.parsed_value, tuple)

    def _parse_value(self) -> int | tuple[int, int] | None:
        if "-" in self._value:
            parts = self._value.split("-")
            if len(parts) == 2:
                try:
                    left = int(parts[0].strip())
                    right = int(parts[1].strip())
                    if left > right:
                        left, right = right, left
                    return (left, right) if left != right else left
                except ValueError:
                    return None

        try:
            return int(self._value.strip())
        except (ValueError, TypeError):
            return None

    def sample(self, context: DistributionContext | None = None) -> float | str:
        """Sample numeric value, else return literal string value."""
        del context
        parsed = self.parsed_value
        if isinstance(parsed, tuple):
            return random.uniform(parsed[0], parsed[1])
        if isinstance(parsed, int):
            return float(parsed)
        return self._value.strip()

    def __str__(self) -> str:
        """Return a readable representation for diagnostics."""
        return f"ProbabilitySegment(percentage={self._percentage}, value='{self._value}')"

    @staticmethod
    def is_matching_segment_data_format(line_value: str) -> re.Match[str] | None:
        """Check whether text matches a supported segment pattern."""
        return re.match(r"(?:\d+:)?\s*\(?\s*(\d+)\s*[,|:]\s*(\d+)\s*-\s*(\d+)\s*\)?", line_value)


class ProbabilityDistribution:
    """Represents a probability distribution with weighted segments."""

    def __init__(self, segments: list[ProbabilitySegment]) -> None:
        """Initialize with one or more weighted segments."""
        if not segments:
            raise ValueError("ProbabilityDistribution must have at least one segment")
        self._segments = segments

    def get_total_percentage(self) -> int:
        """Return the sum of segment percentages."""
        return sum(segment._percentage for segment in self._segments)

    def percentages_exceed_100(self) -> bool:
        """Return whether cumulative percentage exceeds 100."""
        return self.get_total_percentage() > 100

    @property
    def segments(self) -> list[ProbabilitySegment]:
        """Return configured probability segments."""
        return self._segments

    def select_random_segment(self) -> ProbabilitySegment:
        """Choose a segment using normalized weighted sampling."""
        rand = random.random()
        cumulative = 0.0

        total = sum(segment._percentage for segment in self._segments)
        factor = 100.0 / total if total != 0 else 1.0

        for segment in self._segments:
            normalized = (segment._percentage * factor) / 100.0
            cumulative += normalized

            if rand < cumulative:
                return segment

        return self._segments[-1]

    def sample(self, context: DistributionContext | None = None) -> float | str:
        """Sample a value using weighted segment selection."""
        del context
        return self.select_random_segment().sample()

    def __str__(self) -> str:
        """Return a readable representation for diagnostics."""
        segments_str = ",\n".join("\t" + str(s) for s in self._segments)
        return f"ProbabilityDistribution(segments=[\n{segments_str}])"


class EventRateDistribution:
    """Base class for curve distributions that model event rates."""

    def expected_events(self, context: DistributionContext | None = None, horizon_years: float = 1.0) -> float:
        """Return expected event count over the horizon."""
        return max(0.0, self.rate(context) * max(0.0, horizon_years))

    def rate(self, context: DistributionContext | None = None) -> float:
        """Return instantaneous event rate for the given context."""
        raise NotImplementedError

    def sample(self, context: DistributionContext | None = None) -> float:
        """Sample event rate for compatibility with BaseDistribution."""
        return self.rate(context)

    def sample_count(self, context: DistributionContext | None = None, horizon_years: float = 1.0) -> int:
        """Sample an integer count using a Poisson process."""
        lam = self.expected_events(context=context, horizon_years=horizon_years)
        return _sample_poisson(lam)


class NormalCurveDistribution(EventRateDistribution):
    """Bell curve over normalized age ratio."""

    def __init__(
        self,
        baseline_rate: float = 0.1,
        amplitude: float = 0.5,
        mean: float = 0.5,
        stddev: float = 0.2,
    ) -> None:
        """Initialize a Gaussian-shaped event-rate curve."""
        if stddev <= 0:
            raise ValueError("stddev must be > 0")
        self.baseline_rate = baseline_rate
        self.amplitude = amplitude
        self.mean = mean
        self.stddev = stddev

    def rate(self, context: DistributionContext | None = None) -> float:
        """Return event rate based on Gaussian age-ratio response."""
        x = _resolve_age_ratio(context)
        z = (x - self.mean) / self.stddev
        bell = math.exp(-0.5 * z * z)
        return max(0.0, self.baseline_rate + (self.amplitude * bell))


class BathtubCurveDistribution(EventRateDistribution):
    """Piecewise bathtub hazard over normalized age ratio."""

    def __init__(
        self,
        early_peak_rate: float = 0.7,
        useful_life_rate: float = 0.2,
        wearout_peak_rate: float = 0.9,
        early_end_ratio: float = 0.2,
        wearout_start_ratio: float = 0.8,
        max_ratio: float = 1.5,
    ) -> None:
        """Initialize a bathtub-shaped hazard curve."""
        if not (0 <= early_end_ratio < wearout_start_ratio <= max_ratio):
            raise ValueError("Invalid bathtub ratio boundaries")
        self.early_peak_rate = early_peak_rate
        self.useful_life_rate = useful_life_rate
        self.wearout_peak_rate = wearout_peak_rate
        self.early_end_ratio = early_end_ratio
        self.wearout_start_ratio = wearout_start_ratio
        self.max_ratio = max_ratio

    def rate(self, context: DistributionContext | None = None) -> float:
        """Return event rate from early-life, useful-life, and wearout phases."""
        x = _resolve_age_ratio(context, max_ratio=self.max_ratio)

        if x <= self.early_end_ratio:
            if self.early_end_ratio == 0:
                return max(0.0, self.useful_life_rate)
            pct = x / self.early_end_ratio
            value = self.early_peak_rate + (self.useful_life_rate - self.early_peak_rate) * pct
            return max(0.0, value)

        if x < self.wearout_start_ratio:
            return max(0.0, self.useful_life_rate)

        span = max(1e-9, self.max_ratio - self.wearout_start_ratio)
        pct = (x - self.wearout_start_ratio) / span
        value = self.useful_life_rate + (self.wearout_peak_rate - self.useful_life_rate) * pct
        return max(0.0, value)


class PiecewiseCurveDistribution(EventRateDistribution):
    """Linear interpolation over arbitrary (age_ratio, rate) points."""

    def __init__(self, points: list[tuple[float, float]]) -> None:
        """Initialize piecewise linear curve with sorted points."""
        if len(points) < 2:
            raise ValueError("PiecewiseCurveDistribution requires at least two points")
        self.points = sorted(points, key=lambda p: p[0])
        if self.points[0][0] == self.points[-1][0]:
            raise ValueError("Piecewise points must span a non-zero x-range")

    def rate(self, context: DistributionContext | None = None) -> float:
        """Return interpolated event rate for the current age ratio."""
        x = _resolve_age_ratio(context)
        if x <= self.points[0][0]:
            return max(0.0, self.points[0][1])
        if x >= self.points[-1][0]:
            return max(0.0, self.points[-1][1])

        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:], strict=False):
            if x0 <= x <= x1:
                span = max(1e-9, x1 - x0)
                pct = (x - x0) / span
                return max(0.0, y0 + (y1 - y0) * pct)
        return max(0.0, self.points[-1][1])


def create_distribution_from_spec(spec: dict[str, Any]) -> BaseDistribution:
    """Create a distribution from a declarative configuration spec."""
    dist_type = str(spec.get("type", "")).strip().lower()
    if dist_type == "segments":
        raw_segments = spec.get("segments", [])
        segments = [ProbabilitySegment(int(item["percentage"]), str(item["value"])) for item in raw_segments]
        return ProbabilityDistribution(segments)

    if dist_type == "normal":
        return NormalCurveDistribution(
            baseline_rate=float(spec.get("baseline_rate", 0.1)),
            amplitude=float(spec.get("amplitude", 0.5)),
            mean=float(spec.get("mean", 0.5)),
            stddev=float(spec.get("stddev", 0.2)),
        )

    if dist_type == "bathtub":
        return BathtubCurveDistribution(
            early_peak_rate=float(spec.get("early_peak_rate", 0.7)),
            useful_life_rate=float(spec.get("useful_life_rate", 0.2)),
            wearout_peak_rate=float(spec.get("wearout_peak_rate", 0.9)),
            early_end_ratio=float(spec.get("early_end_ratio", 0.2)),
            wearout_start_ratio=float(spec.get("wearout_start_ratio", 0.8)),
            max_ratio=float(spec.get("max_ratio", 1.5)),
        )

    if dist_type == "piecewise":
        points = [(float(x), float(y)) for x, y in spec.get("points", [])]
        return PiecewiseCurveDistribution(points=points)

    raise ValueError(f"Unknown distribution type '{dist_type}'")


def _resolve_age_ratio(context: DistributionContext | None, default_ratio: float = 0.5, max_ratio: float = 1.5) -> float:
    if context is None:
        return default_ratio
    ratio = context.age_ratio
    if ratio is None:
        return default_ratio
    return max(0.0, min(max_ratio, ratio))


def _sample_poisson(lam: float) -> int:
    """Sample Poisson(lam) without external dependencies."""
    if lam <= 0:
        return 0
    l_bound = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l_bound:
        k += 1
        p *= random.random()
    return k - 1
