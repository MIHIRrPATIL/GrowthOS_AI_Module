"""
Deterministic Grounded Metric & Digest Schemas
Conforms to:
- research/docs/GrowthOS_Module_4_AI_Growth_Brain_Architecture_and_Plan.md (Components 1 & 2)

Mathematical Grounding:
Schemas do not eliminate hallucinations alone. Verifiable grounding requires:
1. Strict schema contracts (frozen, extra forbidden, explicit UTC time windows and watermarks).
2. Pure deterministic calculation functions in code (never asking an LLM to compute or estimate math).
3. Immutable evidence references linking computed metrics back to raw event IDs.
4. Rigorous automated tests validated against hand-calculated baselines.
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Literal, Optional, Any, List, Dict
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

Unit = Literal["ratio", "count", "currency_inr", "ms"]
Period = Literal["day_over_day", "week_over_week", "month_over_month"]
Severity = Literal["low", "medium", "high"]
Polarity = Literal["higher_is_better", "lower_is_better"]
MetricStatus = Literal["valid", "insufficient_sample", "zero_denominator", "no_data"]


class TimeWindowPreset(str, Enum):
    """
    Fixed business time-window presets.
    Classifier chooses strictly from this enum; raw ISO timestamps are NEVER hallucinated by the LLM.
    """
    LAST_7D = "last_7d"           # Trailing 7 days from as_of
    PREVIOUS_7D = "previous_7d"   # 7 days preceding trailing 7 days
    THIS_WEEK = "this_week"       # Monday 00:00 UTC to as_of
    LAST_WEEK = "last_week"       # Monday 00:00 to Monday 00:00 of prior week
    LAST_30D = "last_30d"         # Trailing 30 days
    PREVIOUS_30D = "previous_30d" # 30 days preceding trailing 30 days
    TODAY = "today"               # Today 00:00 to as_of
    YESTERDAY = "yesterday"       # Yesterday 00:00 to today 00:00


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TimeWindow(_Strict):
    start: datetime  # inclusive, UTC
    end: datetime    # exclusive, UTC

    @model_validator(mode="after")
    def _ordered(self):
        if self.end <= self.start:
            raise ValueError("window end must be after start")
        return self


def resolve_preset_window(
    preset: str | TimeWindowPreset,
    as_of: datetime
) -> tuple[TimeWindow, Optional[TimeWindow]]:
    """
    Deterministically computes (current_window, prior_window) in code from an enum preset.
    Guarantees mathematically aligned comparisons without LLM hallucinated dates.
    """
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    val = preset.value if isinstance(preset, TimeWindowPreset) else str(preset).lower()

    if val in ("last_7d", "trailing_7d"):
        cur = TimeWindow(start=as_of - timedelta(days=7), end=as_of)
        prior = TimeWindow(start=as_of - timedelta(days=14), end=as_of - timedelta(days=7))
        return cur, prior

    elif val in ("last_week", "previous_week"):
        # Contiguous previous 7-day period (days 7 to 14 prior to as_of)
        cur = TimeWindow(start=as_of - timedelta(days=7), end=as_of)
        prior = TimeWindow(start=as_of - timedelta(days=14), end=as_of - timedelta(days=7))
        return cur, prior

    elif val in ("this_week", "week_to_date", "wtd"):
        # Monday 00:00:00 UTC of current week
        weekday = as_of.weekday()  # 0 is Monday
        start_of_week = as_of.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday)
        if start_of_week >= as_of:
            start_of_week = as_of - timedelta(days=7)
        cur = TimeWindow(start=start_of_week, end=as_of)
        prior_start = start_of_week - timedelta(days=7)
        prior_end = as_of - timedelta(days=7)
        prior = TimeWindow(start=prior_start, end=prior_end)
        return cur, prior

    elif val in ("last_30d", "trailing_30d", "month"):
        cur = TimeWindow(start=as_of - timedelta(days=30), end=as_of)
        prior = TimeWindow(start=as_of - timedelta(days=60), end=as_of - timedelta(days=30))
        return cur, prior

    elif val in ("today", "day_to_date"):
        start_of_day = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
        if start_of_day >= as_of:
            start_of_day = as_of - timedelta(days=1)
        cur = TimeWindow(start=start_of_day, end=as_of)
        prior = TimeWindow(start=start_of_day - timedelta(days=1), end=start_of_day)
        return cur, prior

    elif val in ("yesterday",):
        start_of_day = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
        cur = TimeWindow(start=start_of_day - timedelta(days=1), end=start_of_day)
        prior = TimeWindow(start=start_of_day - timedelta(days=2), end=start_of_day - timedelta(days=1))
        return cur, prior

    # Default fallback: trailing 7 days
    cur = TimeWindow(start=as_of - timedelta(days=7), end=as_of)
    prior = TimeWindow(start=as_of - timedelta(days=14), end=as_of - timedelta(days=7))
    return cur, prior


class MetricResult(_Strict):
    tenant_id: str
    vertical_template_id: str
    metric_name: str                      # must exist in the metric catalog
    definition_version: str
    window: TimeWindow
    as_of: datetime                       # data watermark used for this run
    calculated_at: datetime
    dimensions: dict[str, str] = Field(default_factory=dict)
    numerator: Optional[int] = Field(default=None, ge=0)
    denominator: Optional[int] = Field(default=None, ge=0)
    value: Optional[float] = None         # None when denominator is 0 (undefined ratio)
    status: MetricStatus = "valid"
    unit: Unit
    sample_size: int = Field(ge=0)
    min_sample_threshold: int = Field(default=30, ge=1)
    min_sample_met: bool
    evidence_ref: str                     # stored query specification for deterministic audit trace

    @model_validator(mode="after")
    def _validate_mathematical_consistency(self):
        # 1. Zero Denominator / No Data Guard: 0/0 is undefined, never 0.0
        if self.denominator == 0 or self.sample_size == 0 or self.status in ("zero_denominator", "no_data"):
            if self.value is not None:
                raise ValueError("value must be None when denominator is zero")
            if self.status not in ("zero_denominator", "no_data"):
                raise ValueError("status must be 'zero_denominator' or 'no_data' when denominator is zero")
            if self.min_sample_met:
                raise ValueError("min_sample_met cannot be True when denominator is zero")
            return self

        # 2. Denominator > 0: value must be present
        if self.value is None:
            raise ValueError("value cannot be None when denominator > 0")

        # 3. Ratio Invariant: 0 <= numerator <= denominator and value == numerator / denominator
        if self.unit == "ratio":
            if self.numerator is None or self.denominator is None:
                raise ValueError("numerator and denominator are required for ratio metrics")
            if not (0 <= self.numerator <= self.denominator):
                raise ValueError(
                    f"Ratio invariant violated: numerator ({self.numerator}) must be between 0 and denominator ({self.denominator})"
                )
            if self.sample_size != self.denominator:
                raise ValueError(
                    f"sample_size ({self.sample_size}) must equal denominator ({self.denominator}) for ratios"
                )
            expected_val = self.numerator / self.denominator
            if abs(self.value - expected_val) > 1e-4:
                raise ValueError(
                    f"Mathematical inconsistency: value ({self.value}) != numerator / denominator ({expected_val})"
                )

        # 4. Minimum sample consistency
        expected_min_met = self.sample_size >= self.min_sample_threshold
        if self.min_sample_met != expected_min_met:
            raise ValueError(
                f"min_sample_met ({self.min_sample_met}) contradicts sample_size ({self.sample_size}) vs threshold ({self.min_sample_threshold})"
            )

        if not self.min_sample_met and self.status == "valid":
            raise ValueError("status must be 'insufficient_sample' when min_sample_met is False")

        return self


class DigestFlag(_Strict):
    dedupe_key: str                       # tenant + metric + period + window + tz + ver
    tenant_id: str
    metric_name: str
    period: Period
    polarity: Polarity
    current_value: Optional[float]        # None when undefined
    prior_value: Optional[float]          # None when undefined
    current_sample_size: int = Field(ge=0)
    prior_sample_size: int = Field(ge=0)
    unit: Unit
    threshold_pct: float
    severity: Severity                    # set by rule engine, never by LLM
    adverse: bool                         # did it move in the bad direction?
    flagged_at: datetime
    delta_pp: Optional[float] = None      # percentage point difference for ratios
    is_statistically_significant: Optional[bool] = None
    is_new_activity: bool = False         # True when prior was 0 and current > 0
    lost_conversions: Optional[float] = None  # Estimated lost orders / conversions
    estimated_impact_inr: Optional[float] = None # Estimated monetary loss
    is_primary: bool = True               # True if root bottleneck along funnel, False if downstream
    root_metric_name: Optional[str] = None # Root metric causing this downstream flag
    timezone: str = "UTC"
    status: Literal["active", "acknowledged", "resolved", "insufficient_data"] = "active"

    @computed_field
    @property
    def delta_pct(self) -> Optional[float]:
        if self.prior_value is None or self.current_value is None or self.prior_value == 0:
            return None
        return (self.current_value - self.prior_value) / abs(self.prior_value) * 100


class IdleCartAnomaly(_Strict):
    """
    Component 2: Absence detection work queue item representing an uncompleted recoverable cart.
    Triggered when a customer adds items to cart and remains idle within the recoverable window
    [min_idle_minutes, max_idle_minutes] without converting across this or any other linked session/device.
    """
    anomaly_id: str
    tenant_id: str
    session_id: str
    anonymous_id: str
    customer_id: Optional[str] = None
    cart_total_inr: float
    items: list[dict[str, Any]] = Field(default_factory=list)
    idle_duration_minutes: float
    last_active_at: datetime
    detected_at: datetime
    severity: Severity                    # Driven purely by expected value (e.g. cart total)
    is_recoverable: bool = True           # True if within [min_idle_minutes, max_idle_minutes]
    cooldown_until: Optional[datetime] = None # Cooldown cutoff for recovery messaging
    contactable_channels: list[str] = Field(default_factory=list) # e.g. ["whatsapp", "email", "on_site_prompt"]
    recommended_action: Optional[str] = None # Suggested action signal for Action Proposer (Component 3/6)
    evidence_ref: str


class DigestReport(_Strict):
    report_id: str
    tenant_id: str
    vertical_template_id: str
    period: Period
    current_window: TimeWindow
    prior_window: TimeWindow
    threshold_pct: float
    generated_at: datetime
    current_metrics: dict[str, MetricResult]
    prior_metrics: dict[str, MetricResult]
    flags: list[DigestFlag] = Field(default_factory=list)
    idle_cart_anomalies: list[IdleCartAnomaly] = Field(default_factory=list)
    baseline_type: str = "prior_window"   # 'prior_window' or 'rolling_median'
    baseline_periods_count: int = 1

    @computed_field
    @property
    def flags_count(self) -> int:
        return len(self.flags)

    @computed_field
    @property
    def anomalies_count(self) -> int:
        return len(self.idle_cart_anomalies)

    def adverse_flags(self) -> list[DigestFlag]:
        """Returns only active flags where the metric shifted adversely."""
        return [f for f in self.flags if f.adverse and f.status == "active"]

    def high_severity_flags(self) -> list[DigestFlag]:
        """Returns only high-severity active flags."""
        return [f for f in self.flags if f.severity == "high" and f.status == "active"]

    def primary_flags(self) -> list[DigestFlag]:
        """Returns only primary root bottleneck flags, suppressing downstream echoes."""
        return [f for f in self.flags if f.is_primary and f.status == "active"]


import math


def two_proportion_z_test(
    count1: Optional[int],
    n1: Optional[int],
    count2: Optional[int],
    n2: Optional[int]
) -> tuple[float, float]:
    """
    Performs a standard two-proportion pooled z-test.
    Returns (z_score, two_tailed_p_value).
    Uses math.erfc for pure standard library p-value calculation.
    """
    c1 = count1 or 0
    tot1 = n1 or 0
    c2 = count2 or 0
    tot2 = n2 or 0
    if tot1 <= 0 or tot2 <= 0:
        return 0.0, 1.0

    p1 = c1 / tot1
    p2 = c2 / tot2
    p_pool = (c1 + c2) / (tot1 + tot2)

    variance = p_pool * (1.0 - p_pool) * (1.0 / tot1 + 1.0 / tot2)
    if variance <= 0.0:
        return 0.0, 1.0

    se = math.sqrt(variance)
    z = (p1 - p2) / se
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return z, p_value


def calculate_excess_lost_volume(
    cur_drops: Optional[int],
    cur_entered: Optional[int],
    prior_drops: Optional[int],
    prior_entered: Optional[int]
) -> float:
    """
    Calculates excess lost drop-off volume (sessions/orders) above expected prior baseline rate:
    excess_lost = cur_drops - cur_entered * (prior_drops / prior_entered)
    """
    c_drp = cur_drops or 0
    c_ent = cur_entered or 0
    p_drp = prior_drops or 0
    p_ent = prior_entered or 0
    if p_ent <= 0:
        return float(c_drp)
    prior_rate = p_drp / p_ent
    expected_drops = c_ent * prior_rate
    return round(c_drp - expected_drops, 2)


def format_change_metrics(cur_val: float, prior_val: float) -> str:
    """
    Formats both percentage-point (pp) delta and relative percentage change.
    Example: '+21.4 pp (+75.0% relative)'
    """
    pp_delta = (cur_val - prior_val) * 100.0
    if prior_val > 0.0:
        rel_pct = ((cur_val - prior_val) / prior_val) * 100.0
        return f"{pp_delta:+.1f} pp ({rel_pct:+.1f}% relative)"
    else:
        return f"{pp_delta:+.1f} pp (baseline N/A)"
