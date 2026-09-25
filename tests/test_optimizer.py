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


@pytest.mark.parametrize("penalty", [1e-4, 1, 100])
def test_cycling_penalty_never_sacrifices_optimal_peak(penalty):
    config = BatteryConfig(capacity_mwh=100, max_discharge_mw=20, round_trip_efficiency=1)
    frame = pd.DataFrame({"net_load_mw": [80.0]})
    result = optimize_battery(frame, config, cycling_penalty=penalty)
    assert result.attrs["lp_peak_mw"] == pytest.approx(60, abs=1e-6)


def test_surplus_only_cannot_charge_from_grid_and_never_exports_storage():
    result = optimize_battery(sample_frame(), BatteryConfig(), allow_grid_charging=False)
    net = result.net_load_mw.to_numpy()
    assert np.all(result.lp_charge_mw <= np.maximum(-net, 0) + 1e-6)
    assert np.all(result.lp_discharge_mw <= np.maximum(net, 0) + 1e-6)
    assert not ((result.lp_charge_mw > 1e-6) & (result.lp_discharge_mw > 1e-6)).any()


@pytest.mark.parametrize("dt", [0.25, 1, 2])
def test_optimizer_conserves_stored_energy_each_step(dt):
    config = BatteryConfig(capacity_mwh=50)
    result = optimize_battery(sample_frame(), config, timestep_hours=dt)
    eta = np.sqrt(config.round_trip_efficiency)
    expected = config.capacity_mwh * config.initial_soc_pct / 100 + np.cumsum(
        (result.lp_charge_mw * eta - result.lp_discharge_mw / eta) * dt
    )
    np.testing.assert_allclose(result.lp_soc_pct * config.capacity_mwh / 100, expected, atol=1e-6)


def test_terminal_constraint_is_enforced_and_infeasible_case_is_explicit():
    config = BatteryConfig()
    frame = pd.DataFrame({"net_load_mw": [-100.0, 70.0, 90.0]})
    result = optimize_battery(frame, config, terminal_soc_pct=50, allow_grid_charging=False)
    assert result.lp_soc_pct.iloc[-1] >= 50 - 1e-6
    with pytest.raises(RuntimeError):
        optimize_battery(
            pd.DataFrame({"net_load_mw": [100.0]}), config, terminal_soc_pct=90, allow_grid_charging=False
        )


def test_all_surplus_chooses_no_unnecessary_cycling():
    result = optimize_battery(pd.DataFrame({"net_load_mw": [-50.0] * 10}), BatteryConfig())
    assert result.attrs["lp_peak_mw"] == 0
    assert result.lp_charge_mw.sum() + result.lp_discharge_mw.sum() == pytest.approx(0)


@pytest.mark.parametrize("seed", range(5))
def test_surplus_only_optimum_dominates_heuristic_over_random_profiles(seed):
    net = np.random.default_rng(seed).normal(20, 40, 96)
    frame = pd.DataFrame({"net_load_mw": net})
    config = BatteryConfig(capacity_mwh=80, max_charge_mw=20, max_discharge_mw=20)
    causal = simulate_battery(frame, config, peak_target_mw=30)
    lp = optimize_battery(frame, config, allow_grid_charging=False)
    assert lp.attrs["lp_peak_mw"] <= max(0, causal.optimized_net_load_mw.max()) + 1e-5
