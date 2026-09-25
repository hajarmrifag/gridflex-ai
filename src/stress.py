"""Deterministic stress scenarios with unchanged installed renewable capacity."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .battery import simulate_battery
from .data import scale_renewables
from .flexibility import shift_flexible_demand
from .metrics import calculate_metrics
from .scenarios import ScenarioConfig, run_scenario
from .validation import finite_scalar


def stress_scenario(
    raw: pd.DataFrame, config: ScenarioConfig, demand_shock_pct: float = 25, renewable_drop_pct: float = 40
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Raise demand 17:00–21:00 and derate renewables across the full horizon.

    Keep the original dispatch target and installed generation scale fixed.
    Recompute daily demand shifting against the stressed profile. These are
    sensitivity experiments, not outage probabilities or reliability forecasts.
    """
    finite_scalar(demand_shock_pct, "demand_shock_pct")
    if not 0 <= renewable_drop_pct <= 100:
        raise ValueError("renewable_drop_pct must be between 0 and 100")
    baseline, _ = run_scenario(raw, config)
    stressed = scale_renewables(raw, config.penetration_pct)
    evening = (stressed.index.hour >= 17) & (stressed.index.hour < 21)
    stressed["demand_mw"] *= np.where(evening, 1 + demand_shock_pct / 100, 1)
    stressed[["solar_mw", "wind_mw", "renewable_mw"]] *= 1 - renewable_drop_pct / 100
    flexed = shift_flexible_demand(stressed, config.flexibility_pct)
    result = simulate_battery(flexed, config.battery, baseline.attrs["peak_target_mw"])
    return result, calculate_metrics(result)
