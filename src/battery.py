"""Rule-based battery dispatch with explicit physical constraints."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .validation import finite_columns, finite_scalar


@dataclass(frozen=True)
class BatteryConfig:
    """Technical battery parameters used by the dispatch simulator."""

    capacity_mwh: float = 100.0
    max_charge_mw: float = 35.0
    max_discharge_mw: float = 35.0
    round_trip_efficiency: float = 0.90
    initial_soc_pct: float = 50.0
    min_soc_pct: float = 10.0
    max_soc_pct: float = 95.0

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            finite_scalar(value, name)
        if self.capacity_mwh <= 0:
            raise ValueError("Battery capacity must be positive")
        if self.max_charge_mw < 0 or self.max_discharge_mw < 0:
            raise ValueError("Power limits cannot be negative")
        if not 0 < self.round_trip_efficiency <= 1:
            raise ValueError("Round-trip efficiency must be in (0, 1]")
        if not 0 <= self.min_soc_pct < self.max_soc_pct <= 100:
            raise ValueError("SOC limits must satisfy 0 <= min < max <= 100")
        if not self.min_soc_pct <= self.initial_soc_pct <= self.max_soc_pct:
            raise ValueError("Initial SOC must fall inside the allowed range")


def simulate_battery(
    frame: pd.DataFrame,
    config: BatteryConfig,
    peak_target_mw: float | None = None,
    timestep_hours: float = 1.0,
) -> pd.DataFrame:
    """Dispatch storage into renewable surplus and above a peak target.

    Positive net load is grid import; negative net load is renewable surplus.
    Charging is prioritised whenever surplus exists. Discharge is reserved for
    load above ``peak_target_mw``, making the policy easy to audit.
    """

    finite_scalar(timestep_hours, "timestep_hours", strict=True)
    net = finite_columns(frame, ["net_load_mw"])[:, 0]
    if peak_target_mw is not None:
        finite_scalar(peak_target_mw, "peak_target_mw")

    result = frame.copy()
    if peak_target_mw is None:
        positive = net[net > 0]
        peak_target_mw = float(np.quantile(positive, 0.75)) if positive.size else 0.0

    eta_charge = np.sqrt(config.round_trip_efficiency)
    eta_discharge = np.sqrt(config.round_trip_efficiency)
    min_energy = config.capacity_mwh * config.min_soc_pct / 100
    max_energy = config.capacity_mwh * config.max_soc_pct / 100
    energy = config.capacity_mwh * config.initial_soc_pct / 100

    charge = np.zeros(len(result))
    discharge = np.zeros(len(result))
    soc = np.zeros(len(result))
    post = np.zeros(len(result))

    for i, value in enumerate(net):
        if value < 0:
            available_power = -value
            headroom_power = (max_energy - energy) / (eta_charge * timestep_hours)
            charge[i] = max(0.0, min(available_power, config.max_charge_mw, headroom_power))
            energy += charge[i] * eta_charge * timestep_hours
        elif value > peak_target_mw:
            required_power = value - peak_target_mw
            available_power = (energy - min_energy) * eta_discharge / timestep_hours
            discharge[i] = max(0.0, min(required_power, config.max_discharge_mw, available_power))
            energy -= discharge[i] / eta_discharge * timestep_hours

        post[i] = value + charge[i] - discharge[i]
        soc[i] = 100 * energy / config.capacity_mwh

    result["battery_charge_mw"] = charge
    result["battery_discharge_mw"] = discharge
    result["soc_pct"] = soc
    result["optimized_net_load_mw"] = post
    result.attrs["peak_target_mw"] = peak_target_mw
    result.attrs["battery_config"] = config
    return result
