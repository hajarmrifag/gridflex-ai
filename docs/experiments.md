# Recorded experiments

`experiments.csv` and the three `img/rq*.png` figures were regenerated with GridFlex 0.2.0. Reproduce them with `python scripts/run_experiments.py` after installing the research extra.

Each profile uses its first 60 days, 90% round-trip battery efficiency and a peak target at the 72nd percentile of nonnegative residual load. Battery power is 10% of mean demand; duration sets capacity. Zero storage disables charging and discharging exactly.

The German sample's 24 missing hours are interpolated explicitly. Tétouan renewable generation is estimated from measured weather. Both are historical windows, not representative annual systems.

- RQ1 varies storage duration at 75% renewable penetration with no demand shifting.
- RQ2 compares storage duration and demand shifting at 75% penetration.
- RQ3 varies penetration with and without storage plus flexibility.
- RQ4 compares rule-based and perfect-foresight dispatch with surplus-only charging and no terminal-charge restoration for both controllers. The optimizer minimizes peak import first, then throughput.

The CSV records full-precision metrics. `rq` identifies the experiment; columns not relevant to a particular experiment are empty. Previous README tables used an earlier model and should not be combined with these results.

![Storage duration](img/rq1_storage_duration.png)

![Demand flexibility](img/rq2_flex_vs_storage.png)

![Profile comparison](img/rq3_profile_comparison.png)
