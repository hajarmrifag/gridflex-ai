"""Demand-side flexibility algorithms."""

import numpy as np
import pandas as pd

from .validation import finite_columns, regular_index


def shift_flexible_demand(frame: pd.DataFrame, flexibility_pct: float, window: str = "D") -> pd.DataFrame:
    """Shift a share of demand from high to low residual-load hours.

    Energy is conserved inside each window. The algorithm moves the flexible
    fraction of demand in the highest residual-load quartile and allocates it
    to the lowest quartile, weighted toward renewable-surplus hours.
    """

    if not 0 <= flexibility_pct <= 100:
        raise ValueError("flexibility_pct must be between 0 and 100")
    values = finite_columns(frame, ["demand_mw", "renewable_mw"], nonnegative=True)
    regular_index(frame)

    result = frame.copy()
    demand, renewable = values.T
    shift = np.zeros(len(frame))
    result["original_demand_mw"] = demand
    fraction = flexibility_pct / 100

    groups = frame.groupby(pd.Grouper(freq=window)).indices if fraction else {}
    residual = demand - renewable
    for positions in groups.values():
        if len(positions) < 4:
            continue
        positions = np.asarray(positions)
        local = residual[positions]
        low_cut, high_cut = np.quantile(local, [0.25, 0.75])
        # A flat profile has no high/low distinction; overlapping sets can
        # otherwise manufacture peaks by moving demand back into donor hours.
        if low_cut == high_cut:
            continue
        donors = positions[local >= high_cut]
        receivers = positions[local <= low_cut]
        removed = demand[donors] * fraction
        shift[donors] -= removed
        receiver_residual = residual[receivers]
        attractiveness = receiver_residual.max() - receiver_residual + 1.0
        shift[receivers] += removed.sum() * attractiveness / attractiveness.sum()

    result["demand_shift_mw"] = shift
    result["demand_mw"] = demand + shift
    result["net_load_mw"] = demand + shift - renewable
    return result
