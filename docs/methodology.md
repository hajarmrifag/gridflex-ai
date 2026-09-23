# Methodology

GridFlex is a transparent scenario simulator. It is designed to answer a narrow
question: **how much can a battery and time-shiftable demand improve the use of
variable renewable generation in a simplified power system?**

## Sign convention and balance

For every hourly interval:

```text
net load = demand - wind - solar
grid-facing load = net load + battery charging - battery discharging
```

Positive values are grid imports; negative values are surplus renewable power.
The model does not silently discard energy. Conversion losses appear as a
difference between energy charged and energy later discharged.

## Renewable penetration

The wind and solar profiles retain their historical shapes and technology mix.
They are scaled together until annual renewable energy equals the user-selected
percentage of demand energy. This is a scenario parameter, not a claim about the
historical German generation mix.

## Data sources

GridFlex ships three input profiles, with different provenance:

- **OPSD (Germany):** real historical hourly demand, solar, and wind
  generation, from public grid-operator data via ENTSO-E.
- **Morocco (Tétouan):** real hourly demand from utility SCADA readings
  (Amendis, 2017). Solar and wind are *estimated* from real local irradiance
  and wind-speed measurements at the same substations via standard physical
  conversions, not measured generation — see [`data/README.md`](../data/README.md)
  for the full derivation and the reasoning behind the kW unit assumption.
- **Synthetic stress test:** fully synthetic, seeded for reproducibility, used
  for offline exploration and to exercise edge cases the real samples may not
  cover.

Mixing real demand with an estimated renewable shape (Morocco) is a documented
methodological choice, not an attempt to pass off a simulation as a measurement.
The interface and this document say which parts of each scenario are measured
and which are derived, so no output should be read as more precise than its
source data supports.

## Demand flexibility

For each day, GridFlex identifies the highest and lowest residual-load quartiles.
The selected flexible share is removed from high-load hours and reallocated to
low-load hours. Allocation favours hours with more renewable surplus. Energy is
conserved within every day; this is verified in the automated tests.

The abstraction can represent schedulable EV charging, electric water heating,
industrial loads, or thermal storage. It does not model customer-specific comfort
constraints or rebound effects.

## Battery dispatch

The controller follows two auditable rules:

1. Charge only when residual load is negative (renewable surplus).
2. Discharge only when residual load exceeds the selected peak threshold.

Every step respects energy capacity, charge/discharge power, minimum and maximum
state of charge, and symmetric conversion efficiencies whose product equals the
configured round-trip efficiency.

This heuristic is deliberately interpretable. It is not a claim of globally
optimal dispatch and does not assume perfect electricity prices.

## Metrics

- **Renewable utilisation:** renewable energy not left as residual surplus.
- **Curtailment proxy:** negative grid-facing residual load. In a real system,
  exports or transmission could use some of this energy, so this is an upper bound.
- **Peak reduction:** change in maximum positive grid-facing load.
- **Equivalent cycles:** total charge and discharge throughput divided by twice
  the nameplate energy capacity.
- **Ramp volatility:** standard deviation of hour-to-hour net-load changes.

## Forecasting benchmark

A histogram gradient-boosting model uses hour, weekday, cyclical time features,
and 24/168-hour demand lags. Evaluation is chronological: the final 20% is never
used for fitting. A 24-hour persistence forecast provides a simple baseline.
Forecasting is presented as an analytical benchmark and is not used to make the
rule-based dispatch appear more intelligent than it is.

## Optimizer benchmark

The causal heuristic is also compared against a linear program (`src/optimizer.py`,
solved with SciPy's HiGHS backend) that minimises peak grid import over the full
analysis horizon at once. This LP sees the entire horizon in advance, which no
real controller can, so it is reported strictly as an upper bound: "how much
peak reduction is physically possible from this exact battery, given perfect
information," not a claim about achievable real-time operation.

Both the heuristic and the LP dispatch the same battery on top of the same
demand-flexibility result, so the comparison isolates what the battery itself
contributes rather than crediting the battery for flexibility's share of the
gain. When the battery's power rating is too small relative to the system's
scale to move the peak at all (for example a single grid-scale battery against
Germany's national demand), the app reports that explicitly instead of a
misleading percentage. On scenarios where the battery is a meaningful share of
peak demand, the gap between the heuristic and the LP tends to widen as battery
size grows, because a fixed-threshold rule cannot fully exploit the extra
flexibility a larger battery provides the way full foresight can.

## Limitations and next steps

GridFlex omits transmission constraints, reserve requirements, interconnection,
market prices, battery degradation, network losses, and unit commitment. Useful
extensions include rolling-horizon optimization, degradation-aware dispatch,
and weather-based renewable forecasts. The Morocco sample is a first step
toward a locally sourced case study, not a finished one: it covers one city's
real demand and weather, not a national grid, and its renewable profile is
estimated rather than measured. A fuller version would add real Moroccan
utility-scale solar/wind generation data and a national or regional demand
series, if and when such data becomes openly available.
