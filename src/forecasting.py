"""Small, honest load-forecasting benchmark used for context, not dispatch claims."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error


def forecast_demand(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    """Fit a chronological gradient-boosting benchmark and return holdout predictions."""

    data = frame[["demand_mw"]].copy()
    data["hour"] = data.index.hour
    data["day_of_week"] = data.index.dayofweek
    data["hour_sin"] = np.sin(2 * np.pi * data["hour"] / 24)
    data["hour_cos"] = np.cos(2 * np.pi * data["hour"] / 24)
    data["lag_24h"] = data["demand_mw"].shift(24)
    data["lag_168h"] = data["demand_mw"].shift(168)
    data = data.dropna()
    split = int(len(data) * 0.8)
    train, test = data.iloc[:split], data.iloc[split:]
    features = ["hour", "day_of_week", "hour_sin", "hour_cos", "lag_24h", "lag_168h"]

    model = HistGradientBoostingRegressor(max_iter=150, max_depth=5, learning_rate=0.08)
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
        "improvement_vs_naive_pct": float(100 * (naive_mae - model_mae) / naive_mae),
    }
