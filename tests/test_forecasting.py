import numpy as np
import pytest

from src.data import generate_demo_data
from src.forecasting import forecast_demand


def test_forecast_is_deterministic_and_holdout_is_chronological():
    data = generate_demo_data(14)
    output, metrics = forecast_demand(data)
    again, _ = forecast_demand(data)
    usable = len(data) - 168
    assert len(output) == usable - int(usable * 0.8)
    assert output.index.min() == data.index[168 + int(usable * 0.8)]
    np.testing.assert_allclose(output.forecast_mw, again.forecast_mw)
    np.testing.assert_allclose(output.day_ahead_naive_mw, data.demand_mw.shift(24).loc[output.index])
    assert all(np.isfinite(v) for v in metrics.values())


def test_constant_demand_has_no_undefined_numeric_percentage():
    data = generate_demo_data(14)
    data["demand_mw"] = 100.0
    _, metrics = forecast_demand(data)
    assert metrics["naive_mae_mw"] == 0
    assert metrics["model_mae_mw"] == 0
    assert metrics["improvement_vs_naive_pct"] is None


def test_short_horizon_has_clear_error():
    with pytest.raises(ValueError, match="at least 9 days"):
        forecast_demand(generate_demo_data(7))


def test_imputed_targets_and_lags_are_excluded():
    data = generate_demo_data(30)
    imputed_position = 600
    data.attrs["imputed_timestamps"] = [str(data.index[imputed_position])]
    output, _ = forecast_demand(data)
    assert data.index[imputed_position] not in output.index
    assert data.index[imputed_position + 24] not in output.index
