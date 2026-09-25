"""Compare baseline and optimized kernels in the same Python process/runtime.

Run: python scripts/benchmark.py --baseline-ref 63efed2 --repeats 7
No network or changes to the baseline checkout are needed.
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.battery import BatteryConfig, simulate_battery
from src.data import generate_demo_data, scale_renewables
from src.flexibility import shift_flexible_demand


def median_ms(function, repeats):
    function()
    elapsed = []
    for _ in range(repeats):
        start = time.perf_counter()
        function()
        elapsed.append((time.perf_counter() - start) * 1000)
    return statistics.median(elapsed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="63efed2")
    parser.add_argument("--repeats", type=int, default=7)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    results = []
    with tempfile.TemporaryDirectory() as temp:
        package = Path(temp) / "gridflex_baseline"
        package.mkdir()
        (package / "__init__.py").touch()
        for name in ["battery", "flexibility"]:
            content = subprocess.check_output(["git", "show", f"{args.baseline_ref}:src/{name}.py"], cwd=ROOT)
            (package / f"{name}.py").write_bytes(content)
        sys.path.insert(0, temp)
        old_flex = importlib.import_module("gridflex_baseline.flexibility").shift_flexible_demand
        old_battery = importlib.import_module("gridflex_baseline.battery")
        for days in [30, 60, 365]:
            frame = scale_renewables(generate_demo_data(days), 90)
            pairs = {
                "demand_shifting": (
                    lambda frame=frame: old_flex(frame, 10),
                    lambda frame=frame: shift_flexible_demand(frame, 10),
                ),
                "scenario_pipeline": (
                    lambda frame=frame: old_battery.simulate_battery(
                        old_flex(frame, 10), old_battery.BatteryConfig()
                    ),
                    lambda frame=frame: simulate_battery(shift_flexible_demand(frame, 10), BatteryConfig()),
                ),
            }
            for name, (old, new) in pairs.items():
                before, after = old(), new()
                np.testing.assert_allclose(before.to_numpy(), after.to_numpy(), rtol=1e-10, atol=1e-8)
                baseline_ms, optimized_ms = median_ms(old, args.repeats), median_ms(new, args.repeats)
                results.append(
                    {
                        "operation": name,
                        "days": days,
                        "baseline_ms": round(baseline_ms, 3),
                        "optimized_ms": round(optimized_ms, 3),
                        "speedup": round(baseline_ms / optimized_ms, 2),
                        "max_absolute_difference": float(
                            np.max(np.abs(before.to_numpy() - after.to_numpy()))
                        ),
                    }
                )
    report = {
        "baseline_ref": args.baseline_ref,
        "repeats": args.repeats,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "results": results,
    }
    target = ROOT / "benchmarks" / "latest.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
