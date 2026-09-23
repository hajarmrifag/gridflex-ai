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

## Limitations and next steps

GridFlex omits transmission constraints, reserve requirements, interconnection,
market prices, battery degradation, network losses, and unit commitment. Useful
extensions include rolling-horizon optimization, degradation-aware dispatch,
weather-based renewable forecasts, and a carefully sourced Morocco case study.
