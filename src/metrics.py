"""Evaluation metrics for GridFlex scenarios."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_metrics(frame: pd.DataFrame, timestep_hours: float = 1.0) -> dict[str, float]:
    """Calculate interpretable power-system outcomes from a simulation."""

    baseline = frame["original_demand_mw"] - frame["renewable_mw"]
    optimized = frame["optimized_net_load_mw"]
    baseline_curtailment = (-baseline.clip(upper=0)).sum() * timestep_hours
    optimized_curtailment = (-optimized.clip(upper=0)).sum() * timestep_hours
    renewable_energy = frame["renewable_mw"].sum() * timestep_hours
    discharged = frame["battery_discharge_mw"].sum() * timestep_hours
    charged = frame["battery_charge_mw"].sum() * timestep_hours
    config = frame.attrs.get("battery_config")
    capacity = config.capacity_mwh if config else np.nan

    baseline_peak = float(baseline.clip(lower=0).max())
    optimized_peak = float(optimized.clip(lower=0).max())
    baseline_volatility = float(baseline.diff().dropna().std())
    optimized_volatility = float(optimized.diff().dropna().std())

    return {
        "renewable_utilization_pct": 100
        * (renewable_energy - optimized_curtailment)
        / renewable_energy
        if renewable_energy
        else 0.0,
        "peak_reduction_pct": 100 * (baseline_peak - optimized_peak) / baseline_peak
        if baseline_peak
        else 0.0,
        "baseline_peak_mw": baseline_peak,
        "optimized_peak_mw": optimized_peak,
        "baseline_curtailment_mwh": float(baseline_curtailment),
        "curtailed_renewable_mwh": float(optimized_curtailment),
        "curtailment_avoided_mwh": float(baseline_curtailment - optimized_curtailment),
        "energy_from_storage_mwh": float(discharged),
        "energy_into_storage_mwh": float(charged),
        "equivalent_battery_cycles": float((charged + discharged) / (2 * capacity))
        if capacity and capacity > 0
        else 0.0,
        "baseline_ramp_volatility_mw": baseline_volatility,
        "optimized_ramp_volatility_mw": optimized_volatility,
        "volatility_reduction_pct": 100
        * (baseline_volatility - optimized_volatility)
        / baseline_volatility
        if baseline_volatility
        else 0.0,
    }
