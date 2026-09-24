"""GridFlex AI interactive scenario laboratory."""


from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.battery import BatteryConfig, simulate_battery
from src.data import generate_demo_data, load_timeseries, scale_renewables
from src.flexibility import shift_flexible_demand
from src.forecasting import forecast_demand
from src.metrics import calculate_metrics
from src.optimizer import optimize_battery

st.set_page_config(
    page_title="GridFlex AI",
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


@st.cache_data
def get_data(source: str, days: int) -> pd.DataFrame:
    if source == "Public OPSD sample (Germany)":
        return load_timeseries().iloc[: days * 24]
    if source == "Morocco (Tétouan, real demand + weather)":
        return load_timeseries(MOROCCO_SAMPLE_PATH).iloc[: days * 24]
    return generate_demo_data(days=days)


@st.cache_data
def get_lp_benchmark(frame: pd.DataFrame, config: BatteryConfig) -> pd.DataFrame:
    return optimize_battery(frame, config)


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
    capacity = st.select_slider("Energy capacity (MWh)", [25, 50, 100, 150, 200, 300], value=100)
    power = st.slider("Charge / discharge limit (MW)", 5, 100, 35, 5)
    efficiency = st.slider("Round-trip efficiency", 70, 98, 90, 1, format="%d%%")
    st.markdown("### Flexible demand")
    flexibility = st.slider("Shiftable daily demand", 0, 20, 8, 1, format="%d%%")
    peak_quantile = st.slider("Peak-shaving threshold", 50, 95, 72, 1, format="%dth percentile")
    st.caption("All scenario changes are simulated locally. No black-box optimizer is hiding the assumptions.")

raw = get_data(source, days)
scaled = scale_renewables(raw, penetration)
flexed = shift_flexible_demand(scaled, flexibility)
positive_net = flexed["net_load_mw"].clip(lower=0)
peak_target = float(positive_net.quantile(peak_quantile / 100))
config = BatteryConfig(
    capacity_mwh=capacity,
    max_charge_mw=power,
    max_discharge_mw=power,
    round_trip_efficiency=efficiency / 100,
)
simulated = simulate_battery(flexed, config, peak_target_mw=peak_target)
metrics = calculate_metrics(simulated)
baseline_net = simulated["original_demand_mw"] - simulated["renewable_mw"]

st.caption(
    f"{source}  ·  {len(simulated):,} hourly observations  ·  "
    f"{simulated.index.min():%d %b %Y} → {simulated.index.max():%d %b %Y}"
)
if source == "Morocco (Tétouan, real demand + weather)":
    st.caption(
        "Demand is real (Amendis SCADA, Tétouan, 2017, CC BY 4.0 via UCI ML Repository). "
        "Solar and wind are estimated from real local irradiance and wind-speed readings "
        "at the same substations, not measured generation; see Methodology."
    )

tabs = st.tabs(
    ["System impact", "Dispatch detail", "Forecast lab", "Optimizer benchmark", "Methodology"]
)

with tabs[0]:
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
        before_curt = metrics["baseline_curtailment_mwh"]
        after_curt = metrics["curtailed_renewable_mwh"]
        comparison = go.Figure(go.Bar(
            x=["Peak import (MW)", "Curtailment (MWh)", "Ramp volatility (MW)"],
            y=[metrics["baseline_peak_mw"], before_curt, metrics["baseline_ramp_volatility_mw"]],
            name="Before", marker_color="#52645e",
        ))
        comparison.add_bar(
            x=["Peak import (MW)", "Curtailment (MWh)", "Ramp volatility (MW)"],
            y=[metrics["optimized_peak_mw"], after_curt, metrics["optimized_ramp_volatility_mw"]],
            name="After", marker_color="#65e3a2",
        )
        comparison.update_layout(**chart_layout("Before vs after", "Scenario units"), barmode="group")
        st.plotly_chart(comparison, use_container_width=True)

with tabs[1]:
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

with tabs[2]:
    st.markdown("### Day-ahead demand benchmark")
    st.write("A chronological holdout test compares gradient boosting with a simple 24-hour persistence forecast. Forecasting is kept separate from dispatch so model quality is not confused with flexibility outcomes.")
    try:
        predictions, forecast_metrics = forecast_demand(scaled)
        f1, f2, f3 = st.columns(3)
        f1.metric("Model MAE", f"{forecast_metrics['model_mae_mw']:.2f} MW")
        f2.metric("Naive MAE", f"{forecast_metrics['naive_mae_mw']:.2f} MW")
        f3.metric("Improvement", f"{forecast_metrics['improvement_vs_naive_pct']:.1f}%")
        forecast_fig = go.Figure()
        forecast_fig.add_trace(go.Scatter(x=predictions.index, y=predictions["actual_mw"], name="Actual", line={"color": "#f5f7f6"}))
        forecast_fig.add_trace(go.Scatter(x=predictions.index, y=predictions["forecast_mw"], name="Forecast", line={"color": "#65e3a2"}))
        forecast_fig.update_layout(**chart_layout("Chronological holdout: actual vs forecast"))
        st.plotly_chart(forecast_fig, use_container_width=True)
    except ValueError as exc:
        st.info(f"Select a longer analysis horizon to run the forecast benchmark: {exc}")

with tabs[3]:
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
    run_lp = st.checkbox("Solve the perfect-foresight benchmark", value=True)
    if run_lp:
        lp_result = get_lp_benchmark(flexed, config)
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
        else:
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

with tabs[4]:
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

        - The dispatch controller is causal: no wholesale-market bidding or
          foresight. The optimizer benchmark tab *does* use full-horizon
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

