"""Shared numerical contracts for physical time-series calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def finite_scalar(value: float, name: str, *, minimum: float = 0.0, strict: bool = False) -> None:
    if not np.isfinite(value) or (value <= minimum if strict else value < minimum):
        relation = "greater than" if strict else "at least"
        raise ValueError(f"{name} must be finite and {relation} {minimum}")


def finite_columns(frame: pd.DataFrame, columns: list[str], *, nonnegative: bool = False) -> np.ndarray:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"frame must contain {sorted(missing)}")
    if frame.empty:
        raise ValueError("frame must contain at least one row")
    values = frame[columns].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{columns} must contain only finite values")
    if nonnegative and (values < 0).any():
        raise ValueError(f"{columns} cannot contain negative values")
    return values


def regular_index(frame: pd.DataFrame, *, hourly: bool = False) -> None:
    index = frame.index
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("frame index must be a DatetimeIndex")
    if index.hasnans or not index.is_monotonic_increasing or not index.is_unique:
        raise ValueError("timestamps must be valid, unique, and increasing")
    if len(index) > 1:
        intervals = index[1:] - index[:-1]
        if (intervals != intervals[0]).any():
            raise ValueError("timestamps must be evenly spaced; fill gaps explicitly before simulation")
        if hourly and intervals[0].total_seconds() != 3600:
            raise ValueError("this calculation requires hourly observations")
