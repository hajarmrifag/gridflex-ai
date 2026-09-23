from pathlib import Path

import pandas as pd

from src.data import load_timeseries

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_load_opsd_sample_has_required_columns():
    frame = load_timeseries(DATA_DIR / "opsd_germany_sample.csv")
    assert {"demand_mw", "solar_mw", "wind_mw", "renewable_mw"}.issubset(frame.columns)
    assert isinstance(frame.index, pd.DatetimeIndex)
    assert len(frame) > 0
    assert (frame["demand_mw"] > 0).all()


def test_load_morocco_sample_has_required_columns():
    frame = load_timeseries(DATA_DIR / "morocco_tetouan_sample.csv")
    assert {"demand_mw", "solar_mw", "wind_mw", "renewable_mw"}.issubset(frame.columns)
    assert isinstance(frame.index, pd.DatetimeIndex)
    assert len(frame) > 0
    assert (frame["demand_mw"] > 0).all()
    # Solar/wind are per-unit-capacity shapes (see data/README.md), not
    # absolute installed generation, so they should stay within [0, ~1.2].
    assert frame["solar_mw"].between(0, 1.2).all()
    assert frame["wind_mw"].between(0, 1.2).all()
