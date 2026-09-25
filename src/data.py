"""Input data loading and reproducible demonstration data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .validation import finite_columns, finite_scalar, regular_index


def generate_demo_data(days: int = 30, seed: int = 42) -> pd.DataFrame:
    """Generate a reproducible high-renewables system for offline exploration."""

    if not isinstance(days, int) or isinstance(days, bool) or days < 1:
        raise ValueError("days must be a positive integer")
    rng = np.random.default_rng(seed)
    index = pd.date_range("2024-06-01", periods=days * 24, freq="h", tz="UTC")
    hour = index.hour.to_numpy()
    day = np.arange(len(index)) / 24

    morning = 16 * np.exp(-0.5 * ((hour - 8) / 2.5) ** 2)
    evening = 30 * np.exp(-0.5 * ((hour - 19) / 2.8) ** 2)
    weekly = 5 * np.sin(2 * np.pi * day / 7)
    demand = 78 + morning + evening + weekly + rng.normal(0, 2.5, len(index))

    solar_shape = np.maximum(0, np.sin(np.pi * (hour - 6) / 13)) ** 1.7
    cloud = np.clip(rng.normal(0.84, 0.12, days).repeat(24), 0.35, 1.05)
    solar = 92 * solar_shape * cloud
    wind = np.clip(
        23 + 11 * np.sin(2 * np.pi * day / 4.5 + 1.2) + rng.normal(0, 6, len(index)),
        0,
        None,
    )
    renewable = solar + wind

    return pd.DataFrame(
        {"demand_mw": demand, "solar_mw": solar, "wind_mw": wind, "renewable_mw": renewable},
        index=index,
    )


def load_timeseries(path: str | Path | None = None, *, gap_policy: str = "raise") -> pd.DataFrame:
    """Load an hourly CSV, using the bundled OPSD sample by default.

    Missing or invalid data fails explicitly rather than silently replacing a
    real-data experiment with synthetic observations. ``gap_policy='interpolate'``
    explicitly fills missing hourly observations and records every imputed
    timestamp in ``frame.attrs['imputed_timestamps']``. The bundled German sample
    requires this option: it omits 24 hours on 2015-02-28.
    """

    if gap_policy not in {"raise", "interpolate"}:
        raise ValueError("gap_policy must be 'raise' or 'interpolate'")
    if path is None:
        path = Path(__file__).resolve().parents[1] / "data" / "opsd_germany_sample.csv"
    path = Path(path)
    frame = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
    required = {"demand_mw", "solar_mw", "wind_mw"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset missing columns: {sorted(missing)}")
    frame = frame.sort_index()
    finite_columns(frame, sorted(required), nonnegative=True)
    imputed = []
    if gap_policy == "interpolate" and frame.index.is_unique and not frame.index.hasnans:
        full_index = pd.date_range(frame.index.min(), frame.index.max(), freq="h")
        if not frame.index.isin(full_index).all():
            raise ValueError("interpolation requires observations aligned to an hourly grid")
        missing_hours = full_index.difference(frame.index)
        imputed = missing_hours.astype(str).tolist()
        frame = frame.reindex(full_index).interpolate(method="time")
        frame.index.name = "timestamp"
    regular_index(frame, hourly=True)
    frame["renewable_mw"] = frame["solar_mw"] + frame["wind_mw"]
    frame.attrs["imputed_timestamps"] = imputed
    return frame


def scale_renewables(frame: pd.DataFrame, penetration_pct: float) -> pd.DataFrame:
    """Scale renewable profiles to a requested share of total demand energy."""

    finite_scalar(penetration_pct, "penetration_pct")
    finite_columns(frame, ["demand_mw", "solar_mw", "wind_mw", "renewable_mw"], nonnegative=True)
    result = frame.copy()
    target_energy = result["demand_mw"].sum() * penetration_pct / 100
    current_energy = result["renewable_mw"].sum()
    if target_energy > 0 and current_energy == 0:
        raise ValueError("cannot scale a zero-renewable profile to a positive penetration")
    scale = target_energy / current_energy if current_energy else 0.0
    for column in ("solar_mw", "wind_mw", "renewable_mw"):
        result[column] *= scale
    return result
