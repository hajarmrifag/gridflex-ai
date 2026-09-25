"""Sparse perfect-foresight peak minimization with explicit operating constraints."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from .battery import BatteryConfig
from .validation import finite_columns, finite_scalar


def optimize_battery(
    frame: pd.DataFrame,
    config: BatteryConfig,
    timestep_hours: float = 1.0,
    cycling_penalty: float = 1e-4,
    *,
    allow_grid_charging: bool = True,
    terminal_soc_pct: float | None = None,
) -> pd.DataFrame:
    """Minimize peak import first, then throughput without sacrificing the peak.

    A positive ``cycling_penalty`` enables a second, lexicographic solve; its
    magnitude never trades peak performance for fewer cycles. Zero skips the
    tie-break. Grid charging is retained as the API default for compatibility;
    disable it to match the surplus-only heuristic's operating policy.
    ``terminal_soc_pct`` sets a minimum end-of-horizon SOC, if requested.
    """
    finite_scalar(timestep_hours, "timestep_hours", strict=True)
    finite_scalar(cycling_penalty, "cycling_penalty")
    net = finite_columns(frame, ["net_load_mw"])[:, 0]
    n = len(net)
    if terminal_soc_pct is not None:
        finite_scalar(terminal_soc_pct, "terminal_soc_pct")
        if not config.min_soc_pct <= terminal_soc_pct <= config.max_soc_pct:
            raise ValueError("terminal_soc_pct must fall inside the allowed SOC range")

    eta = float(np.sqrt(config.round_trip_efficiency))
    min_energy = config.capacity_mwh * config.min_soc_pct / 100
    max_energy = config.capacity_mwh * config.max_soc_pct / 100
    initial_energy = config.capacity_mwh * config.initial_soc_pct / 100
    # Layout: charge, discharge, end-of-step energy, peak import.
    n_vars = 3 * n + 1
    t = np.arange(n)
    c_idx, d_idx, e_idx, p_idx = t, n + t, 2 * n + t, 3 * n
    cost = np.zeros(n_vars)
    cost[p_idx] = 1.0

    # Four nonzeros per time step: build directly in NumPy, O(n) storage.
    eq_rows = np.concatenate([t, t, t, t[1:]])
    eq_cols = np.concatenate([e_idx, c_idx, d_idx, e_idx[:-1]])
    eq_vals = np.concatenate(
        [
            np.ones(n),
            np.full(n, -eta * timestep_hours),
            np.full(n, timestep_hours / eta),
            -np.ones(n - 1),
        ]
    )
    a_eq = coo_matrix((eq_vals, (eq_rows, eq_cols)), shape=(n, n_vars)).tocsr()
    eq_rhs = np.zeros(n)
    eq_rhs[0] = initial_energy
    a_ub = coo_matrix(
        (
            np.concatenate([np.ones(n), -np.ones(n), -np.ones(n)]),
            (np.tile(t, 3), np.concatenate([c_idx, d_idx, np.full(n, p_idx)])),
        ),
        shape=(n, n_vars),
    ).tocsr()

    charge_limit = np.full(n, config.max_charge_mw)
    if not allow_grid_charging:
        charge_limit = np.minimum(charge_limit, np.maximum(-net, 0))
    # Batteries supply imports, never export stored energy in this benchmark.
    discharge_limit = np.minimum(config.max_discharge_mw, np.maximum(net, 0))
    bounds = np.column_stack([np.zeros(n_vars), np.zeros(n_vars)])
    bounds[c_idx, 1] = charge_limit
    bounds[d_idx, 1] = discharge_limit
    bounds[e_idx, 0] = min_energy
    bounds[e_idx, 1] = max_energy
    bounds[p_idx, 1] = np.inf
    if terminal_soc_pct is not None:
        bounds[e_idx[-1], 0] = config.capacity_mwh * terminal_soc_pct / 100

    def solve(objective: np.ndarray):
        result = linprog(
            objective,
            A_ub=a_ub,
            b_ub=-net,
            A_eq=a_eq,
            b_eq=eq_rhs,
            bounds=bounds,
            method="highs",
            options={"time_limit": 20.0},
        )
        if not result.success:
            raise RuntimeError(f"Peak-shaving LP failed to solve: {result.message}")
        return result

    result = solve(cost)
    optimum_peak = float(result.x[p_idx])
    peak_tolerance = max(1e-7, abs(optimum_peak) * 1e-9)
    if cycling_penalty > 0:
        bounds[p_idx, 1] = optimum_peak + peak_tolerance
        throughput = np.zeros(n_vars)
        throughput[: 2 * n] = timestep_hours
        result = solve(throughput)

    charge = np.clip(result.x[c_idx], 0, None)
    discharge = np.clip(result.x[d_idx], 0, None)
    out = frame.copy()
    out["lp_charge_mw"] = charge
    out["lp_discharge_mw"] = discharge
    out["lp_soc_pct"] = 100 * result.x[e_idx] / config.capacity_mwh
    out["lp_optimal_net_load_mw"] = net + charge - discharge
    out.attrs.update(
        {
            "lp_peak_mw": float(max(0.0, out["lp_optimal_net_load_mw"].max())),
            "lp_optimum_peak_mw": optimum_peak,
            "lp_peak_tolerance_mw": peak_tolerance,
            "allow_grid_charging": allow_grid_charging,
            "terminal_soc_pct": terminal_soc_pct,
        }
    )
    return out
