"""Systematic GridFlex storage, demand flexibility and profile experiments.

Batteries are sized relative to each system's mean demand so that Tétouan
(~tens of MW) and Germany (~tens of GW) are comparable:

    power  = power_pct  % of mean demand
    energy = duration_h x power

Run from the repository root:  python scripts/run_experiments.py
Outputs: results/*.csv (git-ignored) and docs/img/*.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.battery import BatteryConfig
from src.data import load_timeseries, scale_renewables
from src.flexibility import shift_flexible_demand
from src.optimizer import optimize_battery
from src.scenarios import ScenarioConfig, run_scenario

DAYS = 60
PEAK_QUANTILE = 0.72
EFFICIENCY = 0.90
SYSTEMS = {
    "Morocco (Tétouan)": ROOT / "data" / "morocco_tetouan_sample.csv",
    "Germany": ROOT / "data" / "opsd_germany_sample.csv",
}


def run(raw, penetration, power_pct, duration_h, flex_pct):
    power = raw["demand_mw"].mean() * power_pct / 100
    battery = BatteryConfig(
        capacity_mwh=power * duration_h if duration_h else 1,
        max_charge_mw=power if duration_h else 0,
        max_discharge_mw=power if duration_h else 0,
        round_trip_efficiency=EFFICIENCY,
    )
    _, metrics = run_scenario(raw, ScenarioConfig(penetration, flex_pct, PEAK_QUANTILE, battery))
    return metrics


def main() -> None:
    data = {n: load_timeseries(p, gap_policy="interpolate").iloc[: DAYS * 24] for n, p in SYSTEMS.items()}
    rows = []

    # RQ1: battery energy capacity at fixed power (10% of mean demand), 75% renewables.
    for name, raw in data.items():
        for hours in (0, 1, 2, 4, 8, 12):
            m = run(raw, 75, 10, hours, 0)
            rows.append({"rq": 1, "system": name, "duration_h": hours, **m})
    # RQ2: flexibility vs storage duration (75% renewables, 10% power).
    for name, raw in data.items():
        for flex in (0, 5, 10, 15, 20):
            for hours in (0, 2, 4, 8):
                m = run(raw, 75, 10, hours, flex)
                rows.append({"rq": 2, "system": name, "flex_pct": flex, "duration_h": hours, **m})
    # RQ3: penetration sweep with fixed storage (4 h, 10%) and 10% flexibility, plus no-flex-no-storage.
    for name, raw in data.items():
        for pen in (25, 50, 75, 100, 125):
            for label, (hrs, flex) in {"none": (0, 0), "storage+flex": (4, 10)}.items():
                m = run(raw, pen, 10, hrs, flex)
                rows.append({"rq": 3, "system": name, "penetration": pen, "scenario": label, **m})

    # Benchmark: causal heuristic vs perfect-foresight LP peak reduction (75% renewables, 0% flex).
    for name, raw in data.items():
        scaled = scale_renewables(raw, 75)
        flexed = shift_flexible_demand(scaled, 0)
        base_peak = float(flexed["net_load_mw"].clip(lower=0).max())
        for hours in (2, 4, 8, 12):
            power = raw["demand_mw"].mean() * 0.10
            cfg = BatteryConfig(capacity_mwh=power * hours, max_charge_mw=power,
                                max_discharge_mw=power, round_trip_efficiency=EFFICIENCY)
            lp_peak = optimize_battery(flexed, cfg, allow_grid_charging=False).attrs["lp_peak_mw"]
            rows.append({"rq": 4, "system": name, "duration_h": hours,
                         "lp_peak_reduction_pct": 100 * (base_peak - lp_peak) / base_peak,
                         "heuristic_peak_reduction_pct": run(raw, 75, 10, hours, 0)["peak_reduction_pct"]})

    df = pd.DataFrame(rows)
    (ROOT / "results").mkdir(exist_ok=True)
    df.to_csv(ROOT / "results" / "experiments.csv", index=False)

    img = ROOT / "docs" / "img"
    img.mkdir(parents=True, exist_ok=True)
    colors = {"Morocco (Tétouan)": "#d1495b", "Germany": "#2e6f95"}

    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for name in data:
        d = df[(df.rq == 1) & (df.system == name)]
        ax[0].plot(d.duration_h, d.peak_reduction_pct, "o-", color=colors[name], label=name)
        ax[1].plot(d.duration_h, d.curtailment_avoided_mwh / d.baseline_curtailment_mwh * 100,
                   "o-", color=colors[name], label=name)
        ax[2].plot(d.duration_h, d.renewable_utilization_pct, "o-", color=colors[name], label=name)
    for a, t in zip(ax, ["Peak reduction (%)", "Curtailment avoided (%)", "Renewable utilisation (%)"]):
        a.set_title(t)
        a.set_xlabel("Storage duration at 10% of mean demand (h)")
        a.grid(alpha=0.3)
    ax[0].legend()
    fig.suptitle("RQ1: adding energy capacity at fixed power (75% renewables, 0% flexibility)")
    fig.tight_layout()
    fig.savefig(img / "rq1_storage_duration.png", dpi=130)

    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for a, name in zip(ax, data):
        d = df[(df.rq == 2) & (df.system == name)]
        for hours, ls in ((0, ":"), (2, "--"), (4, "-"), (8, "-.")):
            s = d[d.duration_h == hours]
            a.plot(s.flex_pct, s.peak_reduction_pct, ls, marker="o", label=f"{hours} h storage")
        a.set_title(name)
        a.set_xlabel("Shiftable daily demand (%)")
        a.grid(alpha=0.3)
    ax[0].set_ylabel("Peak reduction (%)")
    ax[0].legend()
    fig.suptitle("RQ2: demand flexibility vs storage duration (75% renewables)")
    fig.tight_layout()
    fig.savefig(img / "rq2_flex_vs_storage.png", dpi=130)

    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for name in data:
        for scen, ls in (("none", "--"), ("storage+flex", "-")):
            d = df[(df.rq == 3) & (df.system == name) & (df.scenario == scen)]
            ax[0].plot(d.penetration, 100 - d.renewable_utilization_pct, ls, marker="o",
                       color=colors[name], label=f"{name}, {scen}")
            ax[1].plot(d.penetration, d.peak_reduction_pct, ls, marker="o", color=colors[name])
    ax[0].set_title("Curtailed share of renewable energy (%)")
    ax[1].set_title("Peak reduction (%)")
    for a in ax:
        a.set_xlabel("Renewable penetration (% of demand energy)")
        a.grid(alpha=0.3)
    ax[0].legend(fontsize=7)
    fig.suptitle("RQ3: same scaling, different local profiles")
    fig.tight_layout()
    fig.savefig(img / "rq3_profile_comparison.png", dpi=130)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    cols = ["peak_reduction_pct", "renewable_utilization_pct", "curtailment_avoided_mwh",
            "baseline_curtailment_mwh", "equivalent_battery_cycles"]
    print(df[df.rq == 1][["system", "duration_h", *cols]].round(2).to_string(index=False))
    print(df[df.rq == 2][["system", "flex_pct", "duration_h", *cols]].round(2).to_string(index=False))
    print(df[df.rq == 4][["system", "duration_h", "lp_peak_reduction_pct", "heuristic_peak_reduction_pct"]].round(2).to_string(index=False))
    print(df[df.rq == 3][["system", "penetration", "scenario", *cols]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
