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
