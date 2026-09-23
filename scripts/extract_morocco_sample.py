"""Build a compact, real-data Morocco case study from the Tetouan City dataset.

Source: Power Consumption of Tetouan City [Dataset]. UCI Machine Learning
Repository (CC BY 4.0). https://doi.org/10.24432/C5B034
Ten-minute SCADA readings collected by Amendis (public utility operator) for
three distribution zones in Tetouan, northern Morocco, across 2017, alongside
local weather measurements (temperature, humidity, wind speed, and two solar
irradiance channels) recorded at the same substations.

This script does three things the raw file does not:

1. Resamples the 10-minute readings to hourly means, matching the rest of the
   app's hourly convention.
2. Converts the three zone power-consumption columns (their units are not
   stated on the UCI page) to a single demand_mw column. We treat them as kW,
   which is the only unit consistent with Morocco's real scale: summed and
   converted this way, city demand comes out to ~40-130 MW, a plausible
   ~1-2% of Morocco's national peak (~8,400 MW per ONEE, 2026). Treating them
   as MW instead would put one mid-sized city above the entire country's
   peak demand, which is physically impossible.
3. Derives *estimated* solar_mw and wind_mw shapes from the real measured
   irradiance and wind speed, using standard simplified conversions. These
   are not measured generation (Tetouan's substations do not host utility-
   scale PV or wind assets) -- they are a physically grounded estimate of
   what a hypothetical local renewable resource would look like, built from
   real local weather. See data/README.md for the full caveat.

Usage:
    python scripts/extract_morocco_sample.py raw_tetouan.csv data/morocco_tetouan_sample.csv
"""

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ZONE_COLUMNS = ["Zone 1 Power Consumption", "Zone 2  Power Consumption", "Zone 3  Power Consumption"]
IRRADIANCE_COLUMN = "general diffuse flows"
WIND_SPEED_COLUMN = "Wind Speed"


def wind_power_curve(speed_ms: np.ndarray, cut_in: float = 3.0, rated: float = 12.0, cut_out: float = 25.0) -> np.ndarray:
    """Standard three-region turbine curve, normalised to 1.0 at rated power."""

    speed = np.asarray(speed_ms, dtype=float)
    return np.where(
        speed < cut_in,
        0.0,
        np.where(
            speed < rated,
            ((speed - cut_in) / (rated - cut_in)) ** 3,
            np.where(speed <= cut_out, 1.0, 0.0),
        ),
    )


def extract(source: Path, destination: Path, rows: int = 1440) -> None:
    frame = pd.read_csv(source)
    frame.columns = [c.strip() for c in frame.columns]
    frame["DateTime"] = pd.to_datetime(frame["DateTime"], format="%m/%d/%Y %H:%M", utc=True)
    frame = frame.set_index("DateTime").sort_index()
    hourly = frame.resample("h").mean()

    demand_mw = hourly[ZONE_COLUMNS].sum(axis=1) / 1000
    solar_mw = (hourly[IRRADIANCE_COLUMN] / 1000).clip(lower=0)
    wind_mw = wind_power_curve(hourly[WIND_SPEED_COLUMN].to_numpy())

    out = pd.DataFrame(
        {
            "timestamp": hourly.index,
            "demand_mw": demand_mw.to_numpy(),
            "solar_mw": solar_mw.to_numpy(),
            "wind_mw": wind_mw,
        }
    ).dropna()

    destination.parent.mkdir(parents=True, exist_ok=True)
    out.iloc[:rows].to_csv(destination, index=False, quoting=csv.QUOTE_MINIMAL)
    written = min(rows, len(out))
    if written < rows:
        raise RuntimeError(f"Only found {written} complete hourly rows; expected {rows}")
    print(f"Wrote {written} hourly records to {destination}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: extract_morocco_sample.py INPUT.csv OUTPUT.csv")
    extract(Path(sys.argv[1]), Path(sys.argv[2]))
