import numpy as np
import pandas as pd

from src.battery import BatteryConfig, simulate_battery


def sample_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=8, freq="h", tz="UTC")
    return pd.DataFrame({"net_load_mw": [-20, -10, 10, 30, 70, 80, 20, -5]}, index=index)


def test_battery_obeys_soc_and_power_limits():
    config = BatteryConfig(capacity_mwh=50, max_charge_mw=15, max_discharge_mw=12)
    result = simulate_battery(sample_frame(), config, peak_target_mw=40)
    assert result["battery_charge_mw"].max() <= 15
    assert result["battery_discharge_mw"].max() <= 12
    assert result["soc_pct"].between(config.min_soc_pct, config.max_soc_pct).all()


def test_dispatch_power_balance():
    result = simulate_battery(sample_frame(), BatteryConfig(), peak_target_mw=40)
    expected = result["net_load_mw"] + result["battery_charge_mw"] - result["battery_discharge_mw"]
    np.testing.assert_allclose(result["optimized_net_load_mw"], expected)


def test_battery_rejects_invalid_efficiency():
    try:
        BatteryConfig(round_trip_efficiency=1.1)
    except ValueError:
        return
    raise AssertionError("Invalid efficiency should raise ValueError")
