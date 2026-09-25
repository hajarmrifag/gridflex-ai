"""Reusable scenario orchestration and comparable storage-sizing experiments."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .battery import BatteryConfig, simulate_battery
from .data import scale_renewables
from .flexibility import shift_flexible_demand
from .metrics import calculate_metrics
from .validation import finite_scalar


@dataclass(frozen=True)
class ScenarioConfig:
    penetration_pct: float = 75.0
    flexibility_pct: float = 8.0
    peak_quantile: float = 0.72
    battery: BatteryConfig = field(default_factory=BatteryConfig)

    def __post_init__(self) -> None:
        finite_scalar(self.penetration_pct, "penetration_pct")
        if not 0 <= self.flexibility_pct <= 100:
            raise ValueError("flexibility_pct must be between 0 and 100")
        if not 0 <= self.peak_quantile <= 1:
            raise ValueError("peak_quantile must be between 0 and 1")


def run_scenario(raw: pd.DataFrame, config: ScenarioConfig) -> tuple[pd.DataFrame, dict[str, float]]:
    scaled = scale_renewables(raw, config.penetration_pct)
    flexed = shift_flexible_demand(scaled, config.flexibility_pct)
    target = float(flexed["net_load_mw"].clip(lower=0).quantile(config.peak_quantile))
    simulated = simulate_battery(flexed, config.battery, peak_target_mw=target)
    return simulated, calculate_metrics(simulated)


def compare_scenarios(
    raw: pd.DataFrame,
    penetration_pct: float = 75.0,
    power_pct: float = 10.0,
    durations: tuple[float, ...] = (0, 2, 4, 8),
    flexibilities: tuple[float, ...] = (0, 5, 10, 15, 20),
    round_trip_efficiency: float = 0.9,
    peak_quantile: float = 0.72,
) -> pd.DataFrame:
    """Sweep duration × demand flexibility with power scaled to the system.

    Scale once, shift once per flexibility level, then reuse each profile for
    the storage sweep. Zero duration is an exact no-storage baseline.
    """
    finite_scalar(power_pct, "power_pct", strict=True)
    if not durations or not flexibilities:
        raise ValueError("provide at least one duration and flexibility level")
    if not 0 <= peak_quantile <= 1:
        raise ValueError("peak_quantile must be between 0 and 1")
    for duration in durations:
        finite_scalar(duration, "duration")
    scaled = scale_renewables(raw, penetration_pct)
    power = float(raw["demand_mw"].mean() * power_pct / 100)
    finite_scalar(power, "system-relative battery power", strict=True)
    rows = []
    for flexibility in flexibilities:
        flexed = shift_flexible_demand(scaled, flexibility)
        target = float(flexed["net_load_mw"].clip(lower=0).quantile(peak_quantile))
        for duration in durations:
            config = BatteryConfig(
                capacity_mwh=power * duration if duration else 1.0,
                max_charge_mw=power if duration else 0.0,
                max_discharge_mw=power if duration else 0.0,
                round_trip_efficiency=round_trip_efficiency,
            )
            result = simulate_battery(flexed, config, peak_target_mw=target)
            rows.append(
                {
                    "duration_h": duration,
                    "flexibility_pct": flexibility,
                    "power_mw": power if duration else 0.0,
                    "capacity_mwh": power * duration,
                    **calculate_metrics(result),
                }
            )
    return pd.DataFrame(rows)
