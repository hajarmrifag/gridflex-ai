# Same-runtime engine benchmark

Recorded on macOS arm64, Python 3.14.7, NumPy 2.5.3, pandas 2.3.3. Each implementation receives the same seeded synthetic profile (90% renewable penetration, 10% demand flexibility). After one warm-up, the script takes the median of seven runs. The old modules are read from Git revision `63efed2` and loaded into a temporary package in the same process as the updated code.

| Operation | Days | Before (ms) | After (ms) | Speedup |
| --- | ---: | ---: | ---: | ---: |
| Demand shifting | 30 | 35.420 | 0.945 | 37.48× |
| Shift + battery | 30 | 36.137 | 1.439 | 25.11× |
| Demand shifting | 60 | 70.982 | 1.498 | 47.38× |
| Shift + battery | 60 | 71.731 | 2.246 | 31.94× |
| Demand shifting | 365 | 435.306 | 6.915 | 62.96× |
| Shift + battery | 365 | 445.389 | 10.139 | 43.93× |

Maximum absolute numeric output difference: **0 in all six cases**. The new flat-quartile behavior is separately tested and intentionally differs from the old algorithm on that edge case. This benchmark does not time HTTP, serialization, browser rendering, forecasts or LP solves. It does not imply an end-to-end application speedup of the same size.

Reproduce from a checkout with the baseline commit available:

```bash
python scripts/benchmark.py --baseline-ref 63efed2 --repeats 7
```

The script asserts numerical equivalence before timing and writes `benchmarks/latest.json` (ignored). [recorded.json](recorded.json) preserves the measurements above. Hardware, interpreter/library versions, background load and thermal conditions affect results. The annual horizon demonstrates core-engine scaling; the public API is capped at 60 days.


## Reproducible measurement records

The harness now warms each variant twice and randomizes baseline/optimized order within each measured pair using a recorded seed. Output includes every sample, pair order, median, sample standard deviation, min/max, row count, full baseline revision, checkout revision/dirty state, source SHA-256 hashes, CPU label and UTC timestamp. The historical `recorded.json` is unchanged and used the earlier timing order; do not silently compare protocols.

```sh
python scripts/benchmark.py --baseline-ref 63efed2 --repeats 7 --order-seed 42 --cpu-label "YOUR ACTUAL CPU" --output benchmarks/review-run.json
```

Use a supported Python >=3.11 environment (the committed API lockfile is one reproducible choice), a quiet machine and several independent runs before claiming a stable speedup. Seven samples do not support a credible p99 estimate; the report deliberately provides raw variability instead. Warmed numerical computation excludes HTTP, queueing, serialization, browser work, forecasting and LP solves. Zero difference in six seeded cases is not universal equivalence; flat-quartile behavior intentionally changed.

The new `review-run.json` records the local verification run. Its source hashes identify the measured implementation even while the feature branch was uncommitted. It is evidence of execution, not a replacement for the historical 31.9x result.
