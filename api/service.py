"""Pure service layer. Shared immutable inputs, bounded process-local caches."""

from dataclasses import asdict
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import pandas as pd

from src.battery import BatteryConfig
from src.data import generate_demo_data, load_timeseries
from src.forecasting import forecast_demand
from src.optimizer import optimize_battery
from src.scenarios import ScenarioConfig, compare_scenarios, run_scenario
from src.stress import stress_scenario

from .models import OptimizeRequest, Profile, ScenarioRequest, StressRequest

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=12)
def profile_data(profile: Profile, days: int) -> pd.DataFrame:
    if profile == Profile.synthetic:
        return generate_demo_data(days)
    name = "morocco_tetouan_sample.csv" if profile == Profile.morocco else "opsd_germany_sample.csv"
    return load_timeseries(ROOT / "data" / name, gap_policy="interpolate").iloc[: days * 24]


def configuration(request: ScenarioRequest) -> tuple[pd.DataFrame, ScenarioConfig]:
    raw = profile_data(request.profile, request.days)
    power = float(raw.demand_mw.mean() * request.power_pct / 100)
    battery = BatteryConfig(
        capacity_mwh=power * request.duration_h if request.duration_h else 1,
        max_charge_mw=power if request.duration_h else 0,
        max_discharge_mw=power if request.duration_h else 0,
        round_trip_efficiency=request.efficiency_pct / 100,
    )
    return raw, ScenarioConfig(
        request.penetration_pct, request.flexibility_pct, request.peak_quantile, battery
    )


def series_payload(frame: pd.DataFrame) -> dict:
    return {
        "timestamps": [stamp.isoformat() for stamp in frame.index],
        "columns": {col: frame[col].to_numpy(dtype=float).tolist() for col in frame.columns},
    }


def metadata(request: ScenarioRequest, config: ScenarioConfig) -> dict:
    raw = profile_data(request.profile, request.days)
    imputed = set(raw.attrs.get("imputed_timestamps", []))
    imputed_hours = sum(stamp in imputed for stamp in raw.index.astype(str))
    return {
        "id": sha256(request.model_dump_json().encode()).hexdigest()[:12],
        "settings": request.model_dump(mode="json"),
        "battery": asdict(config.battery),
        "engine_version": "0.2.0",
        "data_quality": {
            "imputed_hours": imputed_hours,
            "method": "time interpolation" if imputed_hours else "none",
        },
    }


@lru_cache(maxsize=32)
def simulation(request: ScenarioRequest) -> dict:
    raw, config = configuration(request)
    frame, metrics = run_scenario(raw, config)
    return {
        **metadata(request, config),
        "metrics": metrics,
        "series": series_payload(frame),
        "peak_target_mw": frame.attrs["peak_target_mw"],
    }


@lru_cache(maxsize=16)
def comparison(request: ScenarioRequest) -> dict:
    raw, _ = configuration(request)
    result = compare_scenarios(
        raw,
        request.penetration_pct,
        request.power_pct,
        round_trip_efficiency=request.efficiency_pct / 100,
        peak_quantile=request.peak_quantile,
    )
    return {"scenarios": result.to_dict(orient="records")}


@lru_cache(maxsize=12)
def forecast(profile: Profile, days: int) -> dict:
    frame, metrics = forecast_demand(profile_data(profile, days)[["demand_mw"]])
    return {"series": series_payload(frame), "metrics": metrics}


@lru_cache(maxsize=16)
def optimized(request: OptimizeRequest) -> dict:
    raw, config = configuration(request)
    frame, metrics = run_scenario(raw, config)
    terminal = config.battery.initial_soc_pct if request.restore_soc else None
    result = optimize_battery(
        frame[["net_load_mw"]],
        config.battery,
        allow_grid_charging=request.allow_grid_charging,
        terminal_soc_pct=terminal,
    )
    return {
        "series": series_payload(result),
        "peak_mw": result.attrs["lp_peak_mw"],
        "heuristic_peak_mw": metrics["optimized_peak_mw"],
        "optimality_tolerance_mw": result.attrs["lp_peak_tolerance_mw"],
        "allow_grid_charging": request.allow_grid_charging,
        "restore_soc": request.restore_soc,
    }


@lru_cache(maxsize=16)
def stressed(request: StressRequest) -> dict:
    raw, config = configuration(request)
    frame, metrics = stress_scenario(raw, config, request.demand_shock_pct, request.renewable_drop_pct)
    return {
        "series": series_payload(frame),
        "metrics": metrics,
        "peak_target_mw": frame.attrs["peak_target_mw"],
    }
