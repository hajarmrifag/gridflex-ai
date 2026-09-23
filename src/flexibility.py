"""Demand-side flexibility algorithms."""

import pandas as pd


def shift_flexible_demand(
    frame: pd.DataFrame, flexibility_pct: float, window: str = "D"
) -> pd.DataFrame:
    """Shift a share of demand from high to low residual-load hours.

    Energy is conserved inside each window. The algorithm moves the flexible
    fraction of demand in the highest residual-load quartile and allocates it
    to the lowest quartile, weighted toward renewable-surplus hours.
    """

    if not 0 <= flexibility_pct <= 100:
        raise ValueError("flexibility_pct must be between 0 and 100")
    needed = {"demand_mw", "renewable_mw"}
    if not needed.issubset(frame.columns):
        raise ValueError(f"frame must contain {sorted(needed)}")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("frame index must be a DatetimeIndex")

    result = frame.copy()
    result["original_demand_mw"] = result["demand_mw"].astype(float)
    result["demand_shift_mw"] = 0.0
    fraction = flexibility_pct / 100

    if fraction == 0:
        result["net_load_mw"] = result["demand_mw"] - result["renewable_mw"]
        return result

    groups = result.groupby(pd.Grouper(freq=window))
    for _, group in groups:
        if len(group) < 4:
            continue
        residual = group["demand_mw"] - group["renewable_mw"]
        low_cut, high_cut = residual.quantile([0.25, 0.75])
        donor_idx = group.index[residual >= high_cut]
        receiver_idx = group.index[residual <= low_cut]
        if donor_idx.empty or receiver_idx.empty:
            continue

        removed = result.loc[donor_idx, "demand_mw"] * fraction
        shifted_energy = float(removed.sum())
        result.loc[donor_idx, "demand_mw"] -= removed
        result.loc[donor_idx, "demand_shift_mw"] -= removed

        receiver_residual = residual.loc[receiver_idx]
        attractiveness = (receiver_residual.max() - receiver_residual + 1.0).clip(lower=1.0)
        allocation = shifted_energy * attractiveness / attractiveness.sum()
        result.loc[receiver_idx, "demand_mw"] += allocation
        result.loc[receiver_idx, "demand_shift_mw"] += allocation

    result["net_load_mw"] = result["demand_mw"] - result["renewable_mw"]
    return result
