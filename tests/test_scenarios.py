import numpy as np
import pytest

from src.data import generate_demo_data
from src.scenarios import ScenarioConfig, compare_scenarios, run_scenario
from src.stress import stress_scenario


def test_comparison_has_twenty_cases_and_exact_no_storage():
    result = compare_scenarios(generate_demo_data(7))
    assert len(result) == 20
    zero = result[result.duration_h == 0]
    assert (zero.energy_from_storage_mwh == 0).all()
    assert (zero.energy_into_storage_mwh == 0).all()
    assert (zero.equivalent_battery_cycles == 0).all()
    baseline = zero[zero.flexibility_pct == 0].iloc[0]
    assert baseline.peak_reduction_pct == 0
    assert baseline.curtailment_avoided_mwh == 0


def test_stress_does_not_rescale_installed_renewables():
    raw, config = generate_demo_data(7), ScenarioConfig()
    baseline, _ = run_scenario(raw, config)
    stressed, _ = stress_scenario(raw, config, 50, 40)
    np.testing.assert_allclose(stressed.renewable_mw, baseline.renewable_mw * 0.6)
    mask = (raw.index.hour >= 17) & (raw.index.hour < 21)
    np.testing.assert_allclose(stressed.original_demand_mw, raw.demand_mw * np.where(mask, 1.5, 1))
    assert stressed.attrs["peak_target_mw"] == baseline.attrs["peak_target_mw"]


def test_zero_stress_matches_baseline():
    raw, config = generate_demo_data(7), ScenarioConfig()
    _, expected = run_scenario(raw, config)
    _, actual = stress_scenario(raw, config, 0, 0)
    assert actual == pytest.approx(expected)
