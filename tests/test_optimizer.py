import numpy as np
import pandas as pd
import pytest

from src.battery import BatteryConfig, simulate_battery
from src.optimizer import optimize_battery


def sample_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=8, freq="h", tz="UTC")
    return pd.DataFrame({"net_load_mw": [-20, -10, 10, 30, 70, 80, 20, -5]}, index=index)


def test_optimizer_obeys_soc_and_power_limits():
    config = BatteryConfig(capacity_mwh=50, max_charge_mw=15, max_discharge_mw=12)
    result = optimize_battery(sample_frame(), config)
    assert result["lp_charge_mw"].max() <= 15 + 1e-6
    assert result["lp_discharge_mw"].max() <= 12 + 1e-6
    assert result["lp_soc_pct"].between(config.min_soc_pct - 1e-6, config.max_soc_pct + 1e-6).all()


def test_optimizer_power_balance():
    config = BatteryConfig()
    result = optimize_battery(sample_frame(), config)
    expected = result["net_load_mw"] + result["lp_charge_mw"] - result["lp_discharge_mw"]
    np.testing.assert_allclose(result["lp_optimal_net_load_mw"], expected)


def test_optimizer_never_beaten_by_causal_heuristic():
    """The LP sees the whole horizon at once, so it can never do worse than
    the causal rule-based controller on the same scenario and battery."""
    config = BatteryConfig(capacity_mwh=80, max_charge_mw=20, max_discharge_mw=20)
    frame = sample_frame()
    heuristic = simulate_battery(frame, config, peak_target_mw=30)
    optimized = optimize_battery(frame, config)
    heuristic_peak = heuristic["optimized_net_load_mw"].clip(lower=0).max()
    lp_peak = optimized.attrs["lp_peak_mw"]
    assert lp_peak <= heuristic_peak + 1e-6


def test_optimizer_rejects_missing_column():
    with pytest.raises(ValueError):
        optimize_battery(pd.DataFrame({"x": [1, 2, 3]}), BatteryConfig())
