# Data

`opsd_germany_sample.csv` is a compact 60-day extract from:

> Open Power System Data. 2020. Data Package Time series. Version 2020-10-06.
> <https://doi.org/10.25832/time_series/2020-10-06>

The underlying observations originate from the ENTSO-E Transparency Platform.
The extract retains hourly UTC timestamps and Germany-wide actual load, solar,
and wind generation. No imputation is applied; only complete rows are selected.

The historical profiles are rescaled by the app to support counterfactual
renewable-penetration scenarios. Accordingly, scenario values should not be read
as historical German system outcomes.

## `morocco_tetouan_sample.csv`

A compact 60-day, hourly extract built by [`scripts/extract_morocco_sample.py`](../scripts/extract_morocco_sample.py)
from:

> Power Consumption of Tetouan City [Dataset]. UCI Machine Learning Repository, 2020.
> <https://doi.org/10.24432/C5B034> (CC BY 4.0)

The raw file is 10-minute SCADA readings collected across all of 2017 by
Amendis, the public utility operator for Tétouan (northern Morocco), for
three distribution zones, alongside co-located weather measurements
(temperature, humidity, wind speed, and two solar-irradiance channels).

**What is real, and what is derived:**

- `demand_mw` is real measured demand: the three zone power-consumption
  columns, summed and resampled to hourly means. The UCI page does not state
  their units. We treat them as kW (converted to MW here) because that is the
  only unit consistent with Morocco's actual scale; summed this way, city
  demand comes out to ~40–130 MW, a plausible ~1–2% of Morocco's national
  peak (a record 8,400 MW in 2026, per ONEE). Reading them as MW instead would
  put one mid-sized city's demand above the entire country's peak, which is
  not physically possible.
- `solar_mw` and `wind_mw` are **estimated**, not measured. Tétouan's
  substations do not host utility-scale renewable generation; what they do
  record is real local irradiance and wind speed. We convert irradiance to a
  solar shape via the standard STC convention (output scales linearly with
  irradiance relative to 1,000 W/m²) and wind speed to a wind shape via a
  standard three-region turbine power curve (cut-in 3 m/s, rated 12 m/s,
  cut-out 25 m/s). Both are normalised shapes, like the OPSD and synthetic
  sources, the app's own `scale_renewables()` rescales them to whatever
  renewable-penetration percentage the user selects, so the absolute
  nameplate capacity assumed here does not matter.
- Measured wind speeds at these substations average ~2 m/s and rarely near
  turbine rated speed, so the derived wind shape is small; this sample is
  solar-dominated. That is a real property of this data, not a modelling
  choice, and it is broadly consistent with Morocco's renewable mix being
  solar-led outside dedicated wind corridors (e.g. Tarfaya).

This is one city, not a model of Morocco's national grid. See the
[Responsible interpretation](../README.md#responsible-interpretation) section
and [`docs/methodology.md`](../docs/methodology.md) for the full caveats.

## Hourly continuity in the German sample

The bundled German CSV contains 1,440 observations but omits all 24 hours of
2015-02-28. Treating rows as consecutive hours would make SOC transitions and
24/168-hour forecast lags incorrect across that gap.

`load_timeseries()` now rejects irregular timestamps by default. Application and
experiment loaders explicitly request `gap_policy="interpolate"`, which
reindexes to the complete hourly interval, performs time interpolation, and
records the filled timestamps in DataFrame attributes. The raw CSV is unchanged.
The workspace/API disclose the number of interpolated hours within the selected
horizon (24 in the 60-day German case; none in the 30-day case). Forecast fitting
and evaluation exclude interpolated targets and any row whose lag uses them.
These filled values are estimates, not recovered measurements.
