"""Extract a compact Germany case study from the OPSD hourly CSV.

Usage:
    python scripts/extract_opsd_sample.py raw_opsd.csv data/opsd_germany_sample.csv
"""

import csv
import sys
from pathlib import Path

SOURCE_COLUMNS = {
    "utc_timestamp": "timestamp",
    "DE_load_actual_entsoe_transparency": "demand_mw",
    "DE_solar_generation_actual": "solar_mw",
    "DE_wind_generation_actual": "wind_mw",
}


def extract(source: Path, destination: Path, rows: int = 1440) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with source.open(newline="", encoding="utf-8") as src, destination.open(
        "w", newline="", encoding="utf-8"
    ) as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=list(SOURCE_COLUMNS.values()))
        writer.writeheader()
        for row in reader:
            values = {target: row.get(source_name, "") for source_name, target in SOURCE_COLUMNS.items()}
            if not all(values.values()):
                continue
            writer.writerow(values)
            written += 1
            if written >= rows:
                break
    if written < rows:
        raise RuntimeError(f"Only found {written} complete rows; expected {rows}")
    print(f"Wrote {written} hourly records to {destination}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: extract_opsd_sample.py INPUT.csv OUTPUT.csv")
    extract(Path(sys.argv[1]), Path(sys.argv[2]))
