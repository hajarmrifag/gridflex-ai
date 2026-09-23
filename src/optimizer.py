"""Perfect-foresight peak-shaving benchmark, solved as a linear program.

This is deliberately *not* a claim about achievable real-time dispatch: it
sees the entire horizon at once, which no controller can do in operation.
Its purpose is to answer a narrower, defensible question: given the same
battery, how much of the theoretically achievable peak reduction does the
causal, rule-based controller in `battery.py` actually capture?
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from .battery import BatteryConfig


def optimize_battery(
    frame: pd.DataFrame,
    config: BatteryConfig,
    timestep_hours: float = 1.0,
    cycling_penalty: float = 1e-4,
) -> pd.DataFrame:
    """Minimize peak grid import over the full horizon with perfect foresight.

    Formulated as a linear program: minimise the worst-case grid import `P`
    subject to battery power/energy limits and the state-of-charge dynamics.
    A small `cycling_penalty` on total charge/discharge throughput breaks
    ties among equally-optimal-peak solutions in favour of less churn, so
    the result is not just optimal but also interpretable.
    """

    if "net_load_mw" not in frame:
        raise ValueError("frame must contain net_load_mw")
    if timestep_hours <= 0:
        raise ValueError("timestep_hours must be positive")

    net = frame["net_load_mw"].to_numpy(dtype=float)
    n = len(net)
    if n == 0:
        raise ValueError("frame must contain at least one row")

    eta_charge = float(np.sqrt(config.round_trip_efficiency))
    eta_discharge = float(np.sqrt(config.round_trip_efficiency))
    min_energy = config.capacity_mwh * config.min_soc_pct / 100
    max_energy = config.capacity_mwh * config.max_soc_pct / 100
    initial_energy = config.capacity_mwh * config.initial_soc_pct / 100

    # Variable layout: [c_0..c_{n-1}, d_0..d_{n-1}, e_0..e_{n-1}, P]
    n_vars = 3 * n + 1
    c_idx = np.arange(n)
    d_idx = n + np.arange(n)
    e_idx = 2 * n + np.arange(n)
    p_idx = 3 * n

    cost = np.zeros(n_vars)
    cost[c_idx] = cycling_penalty
    cost[d_idx] = cycling_penalty
    cost[p_idx] = 1.0

    # Equality constraints: SOC dynamics, e_t = e_{t-1} + eta_c*dt*c_t - dt/eta_d*d_t
    eq_rows, eq_cols, eq_vals = [], [], []
    eq_rhs = np.zeros(n)
    for t in range(n):
        eq_rows += [t, t, t]
        eq_cols += [e_idx[t], c_idx[t], d_idx[t]]
        eq_vals += [1.0, -eta_charge * timestep_hours, timestep_hours / eta_discharge]
        if t == 0:
            eq_rhs[t] = initial_energy
        else:
            eq_rows.append(t)
            eq_cols.append(e_idx[t - 1])
            eq_vals.append(-1.0)
    a_eq = coo_matrix((eq_vals, (eq_rows, eq_cols)), shape=(n, n_vars)).tocsr()

    # Inequality constraints: net_t + c_t - d_t <= P  =>  c_t - d_t - P <= -net_t
    ub_rows = np.concatenate([np.arange(n), np.arange(n), np.arange(n)])
    ub_cols = np.concatenate([c_idx, d_idx, np.full(n, p_idx)])
    ub_vals = np.concatenate([np.ones(n), -np.ones(n), -np.ones(n)])
    a_ub = coo_matrix((ub_vals, (ub_rows, ub_cols)), shape=(n, n_vars)).tocsr()
    b_ub = -net

    bounds = (
        [(0.0, config.max_charge_mw)] * n
        + [(0.0, config.max_discharge_mw)] * n
        + [(min_energy, max_energy)] * n
        + [(None, None)]
    )

    result = linprog(
        cost,
        A_ub=a_ub,
        b_ub=b_ub,
        A_eq=a_eq,
        b_eq=eq_rhs,
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"Peak-shaving LP failed to solve: {result.message}")

    x = result.x
    charge = np.clip(x[c_idx], 0, None)
    discharge = np.clip(x[d_idx], 0, None)
    soc = 100 * x[e_idx] / config.capacity_mwh

    out = frame.copy()
    out["lp_charge_mw"] = charge
    out["lp_discharge_mw"] = discharge
    out["lp_soc_pct"] = soc
    out["lp_optimal_net_load_mw"] = net + charge - discharge
    out.attrs["lp_peak_mw"] = float(max(0.0, x[p_idx]))
    return out
