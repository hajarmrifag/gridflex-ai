import numpy as np

from src.data import generate_demo_data
from src.flexibility import shift_flexible_demand


def test_demand_shift_conserves_daily_energy():
    source = generate_demo_data(days=5)
    shifted = shift_flexible_demand(source, 12)
    before = source["demand_mw"].resample("D").sum()
    after = shifted["demand_mw"].resample("D").sum()
    np.testing.assert_allclose(before, after, rtol=1e-10)


def test_zero_flexibility_keeps_demand_unchanged():
    source = generate_demo_data(days=2)
    shifted = shift_flexible_demand(source, 0)
    np.testing.assert_allclose(source["demand_mw"], shifted["demand_mw"])
