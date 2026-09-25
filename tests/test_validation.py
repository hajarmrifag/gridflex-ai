import numpy as np
import pandas as pd
import pytest

from src.battery import BatteryConfig, simulate_battery
from src.data import generate_demo_data, load_timeseries, scale_renewables
from src.flexibility import shift_flexible_demand
from src.metrics import calculate_metrics
from src.optimizer import optimize_battery


@pytest.mark.parametrize(
    "field",
    [
        "capacity_mwh",
        "max_charge_mw",
        "max_discharge_mw",
        "round_trip_efficiency",
        "initial_soc_pct",
        "min_soc_pct",
        "max_soc_pct",
    ],
)
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_battery_parameters_are_rejected(field, value):
    with pytest.raises(ValueError):
        BatteryConfig(**{field: value})


@pytest.mark.parametrize("dispatch", [simulate_battery, optimize_battery])
@pytest.mark.parametrize("values", [[], [np.nan], [np.inf]])
def test_dispatch_rejects_empty_or_nonfinite_load(dispatch, values):
    with pytest.raises(ValueError):
        dispatch(pd.DataFrame({"net_load_mw": values}), BatteryConfig())


@pytest.mark.parametrize("dispatch", [simulate_battery, optimize_battery])
@pytest.mark.parametrize("dt", [0, -1, np.nan, np.inf])
def test_invalid_timestep_is_rejected(dispatch, dt):
    with pytest.raises(ValueError):
        dispatch(pd.DataFrame({"net_load_mw": [10]}), BatteryConfig(), timestep_hours=dt)


def test_missing_input_never_silently_becomes_synthetic(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_timeseries(tmp_path / "missing.csv")


@pytest.mark.parametrize("kind", ["gap", "duplicate", "nan", "negative"])
def test_bad_csv_is_rejected(tmp_path, kind):
    frame = generate_demo_data(2)
    if kind == "gap":
        frame = frame.drop(frame.index[2])
    elif kind == "duplicate":
        frame = pd.concat([frame, frame.iloc[[0]]])
    else:
        frame.iloc[0, 0] = np.nan if kind == "nan" else -1
    path = tmp_path / "bad.csv"
    frame.to_csv(path, index_label="timestamp")
    with pytest.raises(ValueError):
        load_timeseries(path)


def test_zero_generation_cannot_be_scaled_to_positive_penetration():
    frame = generate_demo_data(1)
    frame[["solar_mw", "wind_mw", "renewable_mw"]] = 0
    with pytest.raises(ValueError, match="zero-renewable"):
        scale_renewables(frame, 50)
    assert scale_renewables(frame, 0).renewable_mw.sum() == 0


def test_single_observation_metrics_are_finite():
    data = shift_flexible_demand(generate_demo_data(1).iloc[:1], 0)
    metrics = calculate_metrics(simulate_battery(data, BatteryConfig()))
    assert all(np.isfinite(value) for value in metrics.values())


def test_flexibility_handles_integer_inputs_without_truncation():
    data = pd.DataFrame(
        {"demand_mw": [1, 2, 3, 10], "renewable_mw": [0, 0, 0, 0]},
        index=pd.date_range("2024-01-01", periods=4, freq="h"),
    )
    result = shift_flexible_demand(data, 15)
    assert result.demand_mw.tolist() == [2.5, 2, 3, 8.5]
    assert result.demand_mw.sum() == data.demand_mw.sum()


def test_flat_residual_profile_does_not_manufacture_new_peaks():
    data = pd.DataFrame(
        {"demand_mw": [10, 20, 30, 40], "renewable_mw": [0, 10, 20, 30]},
        index=pd.date_range("2024-01-01", periods=4, freq="h"),
    )
    result = shift_flexible_demand(data, 50)
    np.testing.assert_allclose(result.net_load_mw, 10)
    np.testing.assert_allclose(result.demand_shift_mw, 0)


def test_flexibility_does_not_mutate_input_and_conserves_energy_across_dst():
    data = generate_demo_data(4)
    data.index = pd.date_range("2024-03-30", periods=len(data), freq="h", tz="Europe/Berlin")
    original = data.copy(deep=True)
    result = shift_flexible_demand(data, 30)
    pd.testing.assert_frame_equal(data, original)
    np.testing.assert_allclose(data.demand_mw.resample("D").sum(), result.demand_mw.resample("D").sum())
    assert result.demand_mw.min() >= 0
