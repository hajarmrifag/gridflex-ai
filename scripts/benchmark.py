"""Compare baseline and optimized kernels in the same Python process/runtime.

Run: python scripts/benchmark.py --baseline-ref 63efed2 --repeats 7
No network or changes to the baseline checkout are needed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import random
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.battery import BatteryConfig, simulate_battery
from src.data import generate_demo_data, scale_renewables
from src.flexibility import shift_flexible_demand


def paired_timings(old, new, repeats, rng):
    """Warm both variants, then randomize order within each measurement pair."""
    for _ in range(2):
        old()
        new()
    samples = {"baseline": [], "optimized": []}
    orders = []
    for _ in range(repeats):
        pair = [("baseline", old), ("optimized", new)]
        rng.shuffle(pair)
        orders.append([name for name, _ in pair])
        for name, function in pair:
            start = time.perf_counter_ns()
            function()
            samples[name].append((time.perf_counter_ns() - start) / 1e6)
    return samples, orders


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="63efed2")
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "latest.json")
    parser.add_argument("--order-seed", type=int, default=42)
    parser.add_argument("--cpu-label", default=platform.processor() or "not recorded")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    results = []
    rng = random.Random(args.order_seed)
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
                samples, order = paired_timings(old, new, args.repeats, rng)
                baseline_ms = statistics.median(samples["baseline"])
                optimized_ms = statistics.median(samples["optimized"])
                results.append(
                    {
                        "operation": name,
                        "rows": len(frame),
                        "raw_samples_ms": samples,
                        "pair_order": order,
                        "dispersion_ms": {
                            variant: {
                                "min": min(values),
                                "max": max(values),
                                "sample_stdev": statistics.stdev(values) if len(values) > 1 else None,
                            }
                            for variant, values in samples.items()
                        },
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
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "baseline_ref": subprocess.check_output(
            ["git", "rev-parse", args.baseline_ref], cwd=ROOT, text=True
        ).strip(),
        "checkout_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                ROOT / "scripts/benchmark.py",
                ROOT / "src/data.py",
                ROOT / "src/flexibility.py",
                ROOT / "src/battery.py",
            ]
        },
        "cpu": args.cpu_label,
        "warmup_runs_per_variant": 2,
        "order_seed": args.order_seed,
        "method": "randomized paired order; median of raw samples; not service latency",
        "repeats": args.repeats,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "results": results,
    }
    target = args.output
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
