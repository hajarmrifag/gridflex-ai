"""Input data loading and reproducible demonstration data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_demo_data(days: int = 30, seed: int = 42) -> pd.DataFrame:
    """Generate a reproducible high-renewables system for offline exploration."""

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


def load_timeseries(path: str | Path | None = None) -> pd.DataFrame:
    """Load a normalized GridFlex CSV or fall back to the bundled OPSD sample."""

    if path is None:
        path = Path(__file__).resolve().parents[1] / "data" / "opsd_germany_sample.csv"
    path = Path(path)
    if not path.exists():
        return generate_demo_data()

    frame = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
    required = {"demand_mw", "solar_mw", "wind_mw"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset missing columns: {sorted(missing)}")
    frame = frame.sort_index().dropna(subset=list(required))
    frame["renewable_mw"] = frame["solar_mw"] + frame["wind_mw"]
    return frame


def scale_renewables(frame: pd.DataFrame, penetration_pct: float) -> pd.DataFrame:
    """Scale renewable profiles to a requested share of total demand energy."""

    result = frame.copy()
    target_energy = result["demand_mw"].sum() * penetration_pct / 100
    current_energy = result["renewable_mw"].sum()
    scale = target_energy / current_energy if current_energy else 0.0
    for column in ("solar_mw", "wind_mw", "renewable_mw"):
        result[column] *= scale
    return result
