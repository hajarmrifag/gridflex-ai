"""Small, honest load-forecasting benchmark used for context, not dispatch claims."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from .validation import finite_columns, regular_index


def forecast_demand(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | None]]:
    """Fit a chronological gradient-boosting benchmark and return holdout predictions."""

    finite_columns(frame, ["demand_mw"], nonnegative=True)
    regular_index(frame, hourly=True)
    if len(frame) < 216:
        raise ValueError("at least 9 days of hourly data are required for weekly lags and a holdout")
    data = frame[["demand_mw"]].copy()
    data["hour"] = data.index.hour
    data["day_of_week"] = data.index.dayofweek
    data["hour_sin"] = np.sin(2 * np.pi * data["hour"] / 24)
    data["hour_cos"] = np.cos(2 * np.pi * data["hour"] / 24)
    data["lag_24h"] = data["demand_mw"].shift(24)
    data["lag_168h"] = data["demand_mw"].shift(168)
    # Interpolated observations are useful for simulation continuity, but must
    # not manufacture forecast accuracy or provide future-informed lag values.
    imputed = pd.to_datetime(frame.attrs.get("imputed_timestamps", []))
    observed = pd.Series(~frame.index.isin(imputed), index=frame.index)
    usable = observed & observed.shift(24, fill_value=False) & observed.shift(168, fill_value=False)
    data = data.loc[usable]
    data = data.dropna()
    if len(data) < 48:
        raise ValueError(
            "at least 48 usable observations are required after excluding lags and imputed hours"
        )
    split = int(len(data) * 0.8)
    train, test = data.iloc[:split], data.iloc[split:]
    features = ["hour", "day_of_week", "hour_sin", "hour_cos", "lag_24h", "lag_168h"]

    model = HistGradientBoostingRegressor(
        max_iter=150, max_depth=5, learning_rate=0.08, random_state=42, early_stopping=False
    )
    model.fit(train[features], train["demand_mw"])
    prediction = model.predict(test[features])
    naive = test["lag_24h"].to_numpy()
    output = pd.DataFrame(
        {"actual_mw": test["demand_mw"], "forecast_mw": prediction, "day_ahead_naive_mw": naive},
        index=test.index,
    )
    model_mae = mean_absolute_error(output["actual_mw"], output["forecast_mw"])
    naive_mae = mean_absolute_error(output["actual_mw"], output["day_ahead_naive_mw"])
    return output, {
        "model_mae_mw": float(model_mae),
        "naive_mae_mw": float(naive_mae),
        "improvement_vs_naive_pct": float(100 * (naive_mae - model_mae) / naive_mae)
        if naive_mae > 0
        else None,
    }
