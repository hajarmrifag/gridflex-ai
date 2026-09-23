# GridFlex AI

**An interactive battery-dispatch and demand-flexibility laboratory for
renewable power systems.**

GridFlex turns an energy-transition question into a reproducible software
experiment: when wind and solar production do not align with electricity demand,
how much can storage and load shifting reduce peaks and recover surplus energy?

The project is intentionally small enough to audit and serious enough to extend.
It combines hourly public power-system data, physical battery constraints,
energy-conserving demand response, chronological forecasting, and a polished
Streamlit scenario dashboard.

## What makes it useful

- Models state of charge, charge/discharge power, minimum reserve, and losses.
- Shifts flexible demand **within each day without creating or deleting energy**.
- Quantifies peak reduction, renewable utilisation, curtailment, throughput,
  equivalent battery cycles, and residual-load volatility.
- Compares an ML demand forecast against a naive day-ahead baseline on a true
  chronological holdout.
- Exposes every major assumption in the interface and documents limitations.
- Runs offline with the bundled public-data sample or a deterministic stress test.

## Dashboard

The sidebar controls renewable penetration, storage energy and power, round-trip
efficiency, demand flexibility, and the peak-shaving threshold. Four views explain
both the outcome and the mechanism:

1. **System impact** — headline metrics and before/after residual load.
2. **Dispatch detail** — charge, discharge, state of charge, and shifted load.
3. **Forecast lab** — chronological model evaluation against persistence.
4. **Methodology** — assumptions and claims the prototype deliberately avoids.

## Quick start

```bash
git clone <your-repository-url>
cd gridflex-ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open <http://localhost:8501>.

## Architecture

```text
gridflex-ai/
├── app.py                         # Interactive scenario dashboard
├── data/opsd_germany_sample.csv   # 60-day public-data extract
├── docs/methodology.md            # Equations, definitions, limitations
├── scripts/extract_opsd_sample.py # Reproducible data extraction
├── src/
│   ├── battery.py                 # Constrained dispatch controller
│   ├── data.py                    # Loading, synthetic data, scaling
│   ├── flexibility.py             # Energy-conserving load shifting
│   ├── forecasting.py             # Chronological ML benchmark
│   └── metrics.py                 # System-impact evaluation
└── tests/                         # Physics and integration checks
```

## Model flow

```text
hourly demand + wind + solar
              │
              ▼
    renewable scenario scaling
              │
              ▼
 daily flexible-demand shifting
              │
              ▼
 surplus charging / peak discharge
              │
              ▼
 grid-facing residual load + metrics
```

The dispatch policy is causal and interpretable: charge from renewable surplus;
discharge only above a user-selected peak target. It is a heuristic simulator,
not a wholesale-market optimizer. See [the methodology](docs/methodology.md) for
the energy balance, metric definitions, and scope boundaries.

## Data provenance

The bundled Germany sample comes from **Open Power System Data, Time Series
package v2020-10-06**, which compiles hourly electricity load, wind, and solar
generation from sources including ENTSO-E Transparency. The exact attribution
and transformation are recorded in [`data/README.md`](data/README.md).

The app scales these historical shapes to counterfactual renewable shares. This
supports sensitivity analysis; it does **not** recreate Germany's market or grid.
The synthetic mode remains available for offline stress testing.

## Run tests

```bash
pytest
```

The suite checks SOC and power limits, the hourly power balance, daily energy
conservation, invalid configuration handling, and full-pipeline metric behaviour.
GitHub Actions runs tests and linting on every push and pull request.

## Example research questions

- Does a larger battery still help when its power rating stays fixed?
- At what renewable share does curtailment begin to grow rapidly?
- Can 5–10% daily demand flexibility outperform additional battery capacity?
- How does a tighter reserve SOC trade renewable use against peak protection?

## Responsible interpretation

GridFlex is a learning and scenario-analysis tool. It omits transmission,
interconnection, reserve procurement, prices, degradation cost, and generator
commitment. Outputs are not forecasts, operating instructions, or investment
advice. A Morocco/North Africa extension should use locally sourced load and
weather/generation data rather than relabeling the European sample.

## Roadmap

- Rolling-horizon linear optimization with forecast uncertainty.
- Battery degradation and levelized flexibility cost.
- Long-duration storage and interconnector scenarios.
- Open, well-sourced Morocco solar-flexibility case study.
- Scenario export and experiment comparison.

## License

Code is released under the MIT License. Dataset reuse remains subject to the
terms and attribution of its original providers.
