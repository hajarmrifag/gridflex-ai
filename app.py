"""GridFlex interactive scenario laboratory."""


import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.battery import BatteryConfig
from src.data import generate_demo_data, load_timeseries
from src.forecasting import forecast_demand
from src.optimizer import optimize_battery
from src.scenarios import ScenarioConfig, compare_scenarios, run_scenario

st.set_page_config(
    page_title="GridFlex",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #07110f; color: #eefaf3; }
    [data-testid="stSidebar"] { background: #0c1916; border-right: 1px solid #1f3b33; }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #10231d, #0b1815);
        border: 1px solid #244b3e; border-radius: 14px; padding: 15px;
    }
    [data-testid="stMetricValue"] { color: #79f2b1; }
    .hero {
        padding: 1.8rem 2rem; border-radius: 20px; margin-bottom: 1.2rem;
        background: radial-gradient(circle at 85% 10%, #1f684f 0, #102d25 28%, #0b1815 70%);
        border: 1px solid #2a5c4b;
    }
    .eyebrow { color:#72e6aa; text-transform:uppercase; letter-spacing:.18em; font-size:.75rem; }
    .hero h1 { font-size:3rem; margin:.25rem 0; letter-spacing:-.04em; }
    .hero p { max-width:760px; color:#bbd3c8; font-size:1.05rem; }
    .signal { display:inline-block; padding:.25rem .7rem; border-radius:99px; background:#173d31; color:#86f3b9; }
    div[data-testid="stTabs"] button { font-weight:600; }
    </style>
    """,
    unsafe_allow_html=True,
)


MOROCCO_SAMPLE_PATH = Path(__file__).resolve().parent / "data" / "morocco_tetouan_sample.csv"


@st.cache_data(max_entries=32, show_spinner=False)
def get_data(source: str, days: int) -> pd.DataFrame:
    if source == "Public OPSD sample (Germany)":
        return load_timeseries(gap_policy="interpolate").iloc[: days * 24]
    if source == "Morocco (Tétouan, real demand + weather)":
        return load_timeseries(MOROCCO_SAMPLE_PATH).iloc[: days * 24]
    return generate_demo_data(days=days)


@st.cache_data(max_entries=32, show_spinner=False)
def get_lp_benchmark(
    frame: pd.DataFrame, config: BatteryConfig, allow_grid_charging: bool, terminal_soc_pct: float | None
) -> pd.DataFrame:
    return optimize_battery(frame, config, allow_grid_charging=allow_grid_charging,
                            terminal_soc_pct=terminal_soc_pct)


@st.cache_data(max_entries=16, show_spinner=False)
def get_forecast(demand: pd.DataFrame):
    return forecast_demand(demand)


@st.cache_data(max_entries=32, show_spinner=False)
def get_scenario(raw: pd.DataFrame, config: ScenarioConfig):
    return run_scenario(raw, config)


@st.cache_data(max_entries=8, show_spinner=False)
def get_comparison(raw: pd.DataFrame, penetration: float, power_pct: float, efficiency: float, quantile: float):
    return compare_scenarios(raw, penetration, power_pct, round_trip_efficiency=efficiency,
                             peak_quantile=quantile)


def chart_layout(title: str, y_title: str = "MW") -> dict:
    return {
        "title": title,
        "template": "plotly_dark",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 20, "r": 20, "t": 55, "b": 20},
        "hovermode": "x unified",
        "legend": {"orientation": "h", "y": 1.08, "x": 0},
        "yaxis_title": y_title,
        "xaxis": {"showgrid": False},
        "yaxis": {"gridcolor": "#173029"},
    }


st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Renewable power systems · scenario laboratory</div>
      <h1>GridFlex <span style="color:#79f2b1">AI</span></h1>
      <p>Explore how battery dispatch and demand-side flexibility can absorb renewable
      surplus, shave system peaks, and smooth the residual load seen by the grid.</p>
      <span class="signal">● Physics-aware dispatch</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Scenario controls")
    source = st.selectbox(
        "Input profile",
        [
            "Public OPSD sample (Germany)",
            "Morocco (Tétouan, real demand + weather)",
            "Synthetic stress test",
        ],
    )
    days = st.select_slider("Analysis horizon", options=[7, 14, 30, 60], value=30)
    penetration = st.slider("Renewable penetration", 20, 140, 75, 5, format="%d%%")
    st.markdown("### Battery")
    sizing = st.radio("Battery sizing", ["Relative to system", "Absolute MW / MWh"])
    if sizing == "Relative to system":
        power_pct = st.slider("Power (% of mean demand)", 1, 50, 10)
        duration = st.select_slider("Storage duration (hours)", [1, 2, 4, 6, 8, 12], value=4)
    else:
        capacity = st.select_slider("Energy capacity (MWh)", [25, 50, 100, 150, 200, 300], value=100)
        power = st.slider("Charge / discharge limit (MW)", 5, 100, 35, 5)
    efficiency = st.slider("Round-trip efficiency", 70, 98, 90, 1, format="%d%%")
    st.markdown("### Flexible demand")
    flexibility = st.slider("Shiftable daily demand", 0, 20, 8, 1, format="%d%%")
    peak_quantile = st.slider("Peak-shaving threshold", 50, 95, 72, 1, format="%dth percentile")
    st.caption("All scenario changes are simulated locally. No black-box optimizer is hiding the assumptions.")

try:
    raw = get_data(source, days)
except (OSError, ValueError) as exc:
    st.error(f"Could not load the selected profile: {exc}")
    st.stop()
if sizing == "Relative to system":
    power = float(raw["demand_mw"].mean() * power_pct / 100)
    capacity = power * duration
st.sidebar.caption(f"Battery: {power:,.1f} MW / {capacity:,.1f} MWh")
config = BatteryConfig(
    capacity_mwh=capacity, max_charge_mw=power, max_discharge_mw=power,
    round_trip_efficiency=efficiency / 100,
)
scenario = ScenarioConfig(penetration, flexibility, peak_quantile / 100, config)
simulated, metrics = get_scenario(raw, scenario)
peak_target = simulated.attrs["peak_target_mw"]
flexed = simulated[["demand_mw", "renewable_mw", "net_load_mw"]]
baseline_net = simulated["original_demand_mw"] - simulated["renewable_mw"]

st.caption(
    f"{source}  ·  {len(simulated):,} hourly observations  ·  "
    f"{simulated.index.min():%d %b %Y} → {simulated.index.max():%d %b %Y}"
)
imputed = set(raw.attrs.get("imputed_timestamps", []))
imputed_count = sum(stamp in imputed for stamp in raw.index.astype(str))
if imputed_count:
    st.warning(f"{imputed_count} missing hourly observations were time-interpolated. These are estimates, not measurements.")
if source == "Morocco (Tétouan, real demand + weather)":
    st.caption(
        "Demand is real (Amendis SCADA, Tétouan, 2017, CC BY 4.0 via UCI ML Repository). "
        "Solar and wind are estimated from real local irradiance and wind-speed readings "
        "at the same substations, not measured generation; see Methodology."
    )

view = st.radio(
    "Explore the scenario",
    ["System impact", "Dispatch detail", "Scenario lab", "Forecast lab", "Optimizer benchmark", "Methodology"],
    horizontal=True, label_visibility="collapsed", key="view",
)

if view == "System impact":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Peak demand",
        f"{metrics['optimized_peak_mw']:.1f} MW",
        f"{-metrics['peak_reduction_pct']:+.1f}% vs baseline",
        delta_color="inverse",
    )
    c2.metric(
        "Renewable utilisation",
        f"{metrics['renewable_utilization_pct']:.1f}%",
        f"{metrics['curtailment_avoided_mwh']:+.0f} MWh recovered",
    )
    c3.metric(
        "Storage delivered",
        f"{metrics['energy_from_storage_mwh']:.0f} MWh",
        f"{metrics['equivalent_battery_cycles']:.1f} cycles",
        delta_color="off",
    )
    c4.metric(
        "Ramp volatility",
        f"{metrics['optimized_ramp_volatility_mw']:.1f} MW",
        f"{-metrics['volatility_reduction_pct']:+.1f}% vs baseline",
        delta_color="inverse",
    )

    overview = go.Figure()
    overview.add_trace(go.Scatter(x=simulated.index, y=baseline_net, name="Before flexibility", line={"color": "#83938d", "width": 1}))
    overview.add_trace(go.Scatter(x=simulated.index, y=simulated["optimized_net_load_mw"], name="After flexibility", line={"color": "#65e3a2", "width": 2}))
    overview.add_hline(y=0, line_color="#b4c5bd", line_dash="dot")
    overview.add_hline(y=peak_target, line_color="#f4b860", line_dash="dash", annotation_text="Dispatch target")
    overview.update_layout(**chart_layout("Residual load seen by the grid"))
    st.plotly_chart(overview, use_container_width=True)

    left, right = st.columns([1.35, 1])
    with left:
        energy = go.Figure()
        energy.add_trace(go.Scatter(x=simulated.index, y=simulated["demand_mw"], name="Demand", line={"color": "#f3f7f5"}))
        energy.add_trace(go.Scatter(x=simulated.index, y=simulated["renewable_mw"], name="Wind + solar", fill="tozeroy", line={"color": "#44c98a"}, opacity=.65))
        energy.update_layout(**chart_layout("Demand and renewable production"))
        st.plotly_chart(energy, use_container_width=True)
    with right:
        st.markdown("### Impact at a glance")
        st.dataframe(pd.DataFrame({
            "Measure": ["Peak import (MW)", "Curtailment (MWh)", "Ramp volatility (MW)"],
            "Before": [metrics["baseline_peak_mw"], metrics["baseline_curtailment_mwh"],
                       metrics["baseline_ramp_volatility_mw"]],
            "After": [metrics["optimized_peak_mw"], metrics["curtailed_renewable_mwh"],
                      metrics["optimized_ramp_volatility_mw"]],
        }).round(2), hide_index=True, use_container_width=True)
        st.caption("Power, energy and volatility use different units; compare each row independently.")
        st.download_button("Download scenario settings", json.dumps({
            "source": source, "days": days, **asdict(scenario), "metrics": metrics,
        }, indent=2), "gridflex_scenario.json", "application/json")

if view == "Dispatch detail":
    st.markdown("### What the controller is doing")
    st.write("The battery charges only from renewable surplus and discharges only above the selected peak target. Flexible demand is shifted within each day, so total daily energy is conserved.")
    dispatch = go.Figure()
    dispatch.add_trace(go.Bar(x=simulated.index, y=-simulated["battery_charge_mw"], name="Charging", marker_color="#36a9e1"))
    dispatch.add_trace(go.Bar(x=simulated.index, y=simulated["battery_discharge_mw"], name="Discharging", marker_color="#ffb45b"))
    dispatch.add_trace(go.Scatter(x=simulated.index, y=simulated["soc_pct"], name="State of charge", yaxis="y2", line={"color": "#79f2b1", "width": 2}))
    dispatch.update_layout(
        **chart_layout("Battery operations", "Battery power (MW)"),
        yaxis2={"title": "State of charge (%)", "overlaying": "y", "side": "right", "range": [0, 100], "showgrid": False},
        barmode="relative",
    )
    st.plotly_chart(dispatch, use_container_width=True)

    shifted = go.Figure()
    shifted.add_trace(go.Bar(x=simulated.index, y=simulated["demand_shift_mw"].clip(upper=0), name="Load moved away", marker_color="#e66f6f"))
    shifted.add_trace(go.Bar(x=simulated.index, y=simulated["demand_shift_mw"].clip(lower=0), name="Load moved here", marker_color="#65e3a2"))
    shifted.update_layout(**chart_layout("Daily demand shifting", "Shift (MW)"), barmode="relative")
    st.plotly_chart(shifted, use_container_width=True)
    with st.expander("Inspect simulation data"):
        st.dataframe(simulated.round(2), use_container_width=True)
        st.download_button("Download scenario CSV", simulated.to_csv().encode(), "gridflex_scenario.csv", "text/csv")

if view == "Scenario lab":
    st.markdown("### Find the useful storage size")
    st.write("Compare 20 combinations of storage duration and demand flexibility on the same profile. "
             "Battery power is sized against mean demand so the comparison works at city and national scale.")
    comparison_power = st.slider("Comparison power (% of mean demand)", 1, 50, 10)
    with st.spinner("Comparing storage and flexibility scenarios…"):
        comparison = get_comparison(raw, penetration, comparison_power, efficiency / 100, peak_quantile / 100)
    measure = st.selectbox("Compare by", ["peak_reduction_pct", "renewable_utilization_pct", "curtailment_avoided_mwh"],
                           format_func=lambda x: {"peak_reduction_pct": "Peak reduction (%)",
                           "renewable_utilization_pct": "Renewable utilisation (%)",
                           "curtailment_avoided_mwh": "Curtailment avoided (MWh)"}[x])
    matrix = comparison.pivot(index="flexibility_pct", columns="duration_h", values=measure)
    heatmap = go.Figure(go.Heatmap(
        x=[f"{v:g} h" for v in matrix.columns], y=[f"{v:g}%" for v in matrix.index],
        z=matrix.to_numpy(), colorscale="Greens", text=matrix.round(1).to_numpy(),
        texttemplate="%{text}", hovertemplate="Storage: %{x}<br>Flexibility: %{y}<br>Value: %{z:.2f}<extra></extra>",
    ))
    heatmap.update_layout(**chart_layout("Storage × demand flexibility", "Flexible demand"),
                          xaxis_title="Storage duration")
    st.plotly_chart(heatmap, use_container_width=True)
    st.caption("0 h is an exact no-storage baseline. A higher flexible share can create new peaks; "
               "these results describe the heuristic, not guaranteed savings or investment returns.")
    st.dataframe(comparison.round(3), hide_index=True, use_container_width=True)
    st.download_button("Download comparison CSV", comparison.to_csv(index=False),
                       "gridflex_comparison.csv", "text/csv")

if view == "Forecast lab":
    st.markdown("### Day-ahead demand benchmark")
    st.write("A chronological holdout test compares gradient boosting with a simple 24-hour persistence forecast. Forecasting is kept separate from dispatch so model quality is not confused with flexibility outcomes.")
    try:
        with st.spinner("Training the chronological benchmark…"):
            predictions, forecast_metrics = get_forecast(raw[["demand_mw"]])
        f1, f2, f3 = st.columns(3)
        f1.metric("Model MAE", f"{forecast_metrics['model_mae_mw']:.2f} MW")
        f2.metric("Naive MAE", f"{forecast_metrics['naive_mae_mw']:.2f} MW")
        improvement = forecast_metrics["improvement_vs_naive_pct"]
        f3.metric("Improvement", f"{improvement:.1f}%" if improvement is not None else "N/A")
        if improvement is None:
            st.caption("The persistence baseline has zero error, so percentage improvement is undefined.")
        forecast_fig = go.Figure()
        forecast_fig.add_trace(go.Scatter(x=predictions.index, y=predictions["actual_mw"], name="Actual", line={"color": "#f5f7f6"}))
        forecast_fig.add_trace(go.Scatter(x=predictions.index, y=predictions["forecast_mw"], name="Forecast", line={"color": "#65e3a2"}))
        forecast_fig.update_layout(**chart_layout("Chronological holdout: actual vs forecast"))
        st.plotly_chart(forecast_fig, use_container_width=True)
    except ValueError as exc:
        st.info(f"Select a longer analysis horizon to run the forecast benchmark: {exc}")

if view == "Optimizer benchmark":
    st.markdown("### How close is the heuristic to the theoretical best?")
    st.write(
        "The dispatch tabs above use a causal rule: charge on surplus, discharge above a "
        "fixed peak target. This benchmark instead solves a linear program with perfect "
        "foresight of the whole horizon, so it can plan ahead in a way no real controller "
        "can. It is not a claim about achievable operation; it is an upper bound the "
        "heuristic can be measured against."
    )
    st.caption(
        "Demand flexibility is applied identically before either dispatch method runs, so "
        "the comparison below isolates what the battery itself contributes, on top of "
        "flexibility, rather than crediting the battery for flexibility's share of the gain."
    )
    allow_grid = st.checkbox("Allow charging from the grid", value=False)
    restore_soc = st.checkbox("Restore initial charge by the end of the horizon", value=False)
    st.caption("Default: surplus-only charging, matching the heuristic. Restoring charge adds a stricter "
               "terminal constraint that the heuristic does not enforce; the capture ratio is hidden in that mode.")
    run_lp = st.checkbox("Solve the perfect-foresight benchmark", value=True)
    if run_lp:
        try:
            with st.spinner("Solving peak import, then minimum cycling…"):
                lp_result = get_lp_benchmark(
                    flexed, config, allow_grid, config.initial_soc_pct if restore_soc else None
                )
        except RuntimeError as exc:
            st.warning(f"This benchmark could not be solved. The selected terminal charge may be infeasible. {exc}")
            st.stop()
        lp_peak = lp_result.attrs["lp_peak_mw"]
        baseline_peak = float(baseline_net.clip(lower=0).max())
        no_battery_peak = float(flexed["net_load_mw"].clip(lower=0).max())
        heuristic_peak = metrics["optimized_peak_mw"]
        battery_achievable = no_battery_peak - lp_peak

        o1, o2, o3, o4 = st.columns(4)
        o1.metric("Baseline peak", f"{baseline_peak:.1f} MW")
        o2.metric("After flexibility, no battery", f"{no_battery_peak:.1f} MW")
        o3.metric("Heuristic peak", f"{heuristic_peak:.1f} MW")
        o4.metric("LP-optimal peak", f"{lp_peak:.1f} MW")

        if battery_achievable < max(0.005 * no_battery_peak, 1e-6):
            st.info(
                "The battery's power rating is too small relative to this system's peak "
                "for storage-driven peak-shaving to move the needle here; both the "
                "heuristic and the theoretical optimum leave the post-flexibility peak "
                "almost unchanged. Try the synthetic stress test or a larger battery to "
                "see the gap widen."
            )
        elif not restore_soc:
            captured_pct = 100 * (no_battery_peak - heuristic_peak) / battery_achievable
            st.metric(
                "Heuristic captures",
                f"{captured_pct:.0f}% of the battery's achievable peak reduction",
            )

        lp_fig = go.Figure()
        lp_fig.add_trace(go.Scatter(x=simulated.index, y=baseline_net, name="Baseline", line={"color": "#83938d", "width": 1}))
        lp_fig.add_trace(go.Scatter(x=flexed.index, y=flexed["net_load_mw"], name="After flexibility, no battery", line={"color": "#5a7a6d", "width": 1, "dash": "dot"}))
        lp_fig.add_trace(go.Scatter(x=simulated.index, y=simulated["optimized_net_load_mw"], name="Heuristic", line={"color": "#65e3a2", "width": 2}))
        lp_fig.add_trace(go.Scatter(x=lp_result.index, y=lp_result["lp_optimal_net_load_mw"], name="LP-optimal (perfect foresight)", line={"color": "#f4b860", "width": 2, "dash": "dot"}))
        lp_fig.add_hline(y=0, line_color="#b4c5bd", line_dash="dot")
        lp_fig.update_layout(**chart_layout("Baseline vs heuristic vs perfect-foresight optimum"))
        st.plotly_chart(lp_fig, use_container_width=True)
    else:
        st.caption("Enable the checkbox to solve the benchmark for the current scenario.")

if view == "Methodology":
    st.markdown("### Transparent by design")
    a, b = st.columns(2)
    with a:
        st.markdown("""
        **Dispatch sequence**

        1. Scale the wind and solar profile to the scenario penetration.
        2. Shift the selected demand share from high to low residual-load hours.
        3. Charge the battery from renewable surplus, subject to power and SOC limits.
        4. Discharge above the peak target, accounting for conversion losses.
        5. Compare grid-facing residual load before and after intervention.
        """)
    with b:
        st.markdown("""
        **What this prototype does not claim**

        - Battery decisions use the current state and a fixed threshold. The
          threshold and daily demand shifting use the selected historical profile,
          so the complete experiment is retrospective. The optimizer benchmark tab *does* use full-horizon
          foresight, but only to measure an upper bound, never as a claim
          about what a real controller could execute in operation.
        - No transmission constraints, ancillary services, or degradation cost.
        - OPSD is a European case study; the Morocco sample is one city
          (Tétouan), not a model of Morocco's national grid.
        - In the Morocco sample, only demand is measured. Solar and wind are
          *estimated* from real local irradiance and wind-speed readings via
          a standard conversion, not measured generation.
        - Results show scenario sensitivity, not an investment recommendation.
        """)
    st.info("Core design principle: every headline metric can be traced back to an hourly power balance.")
