from src.battery import BatteryConfig, simulate_battery
from src.data import generate_demo_data, scale_renewables
from src.flexibility import shift_flexible_demand
from src.metrics import calculate_metrics


def test_full_pipeline_produces_finite_metrics():
    data = scale_renewables(generate_demo_data(days=14), 90)
    flexed = shift_flexible_demand(data, 10)
    simulated = simulate_battery(flexed, BatteryConfig(), peak_target_mw=70)
    metrics = calculate_metrics(simulated)
    assert metrics["optimized_peak_mw"] <= metrics["baseline_peak_mw"]
    assert metrics["energy_from_storage_mwh"] >= 0
    assert 0 <= metrics["renewable_utilization_pct"] <= 100
