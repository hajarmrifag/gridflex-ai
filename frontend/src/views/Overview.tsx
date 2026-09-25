import { useState } from "react";
import {
  ArrowDownRight,
  BatteryCharging,
  CircleHelp,
  Leaf,
  MoveUpRight,
  Waves,
  Zap,
} from "lucide-react";
import { Chart, Legend } from "../components/Chart";
import { Metric, Panel } from "../components/UI";
import { EnergyFlow } from "../components/EnergyFlow";
import { format } from "../types";
import type { Simulation, View } from "../types";

export default function Overview({
  data,
  onNavigate,
}: {
  data: Simulation;
  onNavigate: (view: View) => void;
}) {
  const [window, setWindow] = useState(168);
  const {
    metrics: m,
    series: { columns: c, timestamps: t },
  } = data;
  const n = Math.min(window || t.length, t.length);
  const baseline = c.original_demand_mw.map((v, i) => v - c.renewable_mw[i]);
  const lines = [
    {
      name: "Before flexibility",
      values: baseline.slice(0, n),
      color: "#77938a",
      dashed: true,
    },
    {
      name: "After flexibility",
      values: c.optimized_net_load_mw.slice(0, n),
      color: "#b9f28b",
      fill: true,
    },
  ];
  const peakIndex = c.optimized_net_load_mw.indexOf(
    Math.max(...c.optimized_net_load_mw),
  );
  const recovery = m.baseline_curtailment_mwh
    ? (100 * m.curtailment_avoided_mwh) / m.baseline_curtailment_mwh
    : 0;
  return (
    <>
      <div className="metric-grid">
        <Metric
          label="Peak grid demand"
          value={format(m.optimized_peak_mw)}
          unit="MW"
          note={`${format(m.peak_reduction_pct)}% reduction from baseline`}
          icon={<Zap size={17} />}
        />
        <Metric
          label="Renewables used"
          value={format(m.renewable_utilization_pct)}
          unit="%"
          note={`${format(m.curtailment_avoided_mwh, 0)} MWh surplus recovered`}
          icon={<Leaf size={17} />}
          accent="teal"
        />
        <Metric
          label="Storage delivered"
          value={format(m.energy_from_storage_mwh, 0)}
          unit="MWh"
          note={`${format(m.equivalent_battery_cycles)} equivalent cycles`}
          icon={<BatteryCharging size={17} />}
          accent="amber"
        />
        <Metric
          label="Ramp volatility"
          value={format(m.optimized_ramp_volatility_mw)}
          unit="MW"
          note={`${format(m.volatility_reduction_pct)}% reduction from baseline`}
          icon={<Waves size={17} />}
          accent="blue"
        />
      </div>
      <Panel
        title="A smoother path to renewable power."
        eyebrow="GRID-FACING RESIDUAL LOAD"
        className="dark-panel"
        action={
          <div className="period-switch">
            {[
              [24, "24H"],
              [168, "7D"],
              [0, "ALL"],
            ].map(([v, label]) => (
              <button
                key={v}
                className={window === v ? "active" : ""}
                onClick={() => setWindow(Number(v))}
              >
                {label}
              </button>
            ))}
          </div>
        }
      >
        <div className="chart-summary">
          <span>
            <b>{format(m.baseline_peak_mw)}</b> MW peak before
          </span>
          <ArrowDownRight size={22} />
          <span className="lime">
            <b>{format(m.optimized_peak_mw)}</b> MW after
          </span>
          <span className="chart-note">
            {n.toLocaleString()} hourly observations
          </span>
        </div>
        <Chart lines={lines} timestamps={t.slice(0, n)} dark height={280} />
        <div className="chart-footer">
          <Legend lines={lines} />
          <span>
            Negative load = renewable surplus <CircleHelp size={13} />
          </span>
        </div>
      </Panel>
      <div className="two-column overview-bottom">
        <Panel
          title="The system at its peak"
          eyebrow="ENERGY FLOW"
          action={
            <button
              className="icon-button"
              aria-label="Open dispatch replay"
              onClick={() => onNavigate("dispatch")}
            >
              <MoveUpRight size={18} />
            </button>
          }
        >
          <EnergyFlow
            solar={c.solar_mw[peakIndex]}
            wind={c.wind_mw[peakIndex]}
            demand={c.demand_mw[peakIndex]}
            charge={c.battery_charge_mw[peakIndex]}
            discharge={c.battery_discharge_mw[peakIndex]}
            net={c.optimized_net_load_mw[peakIndex]}
            soc={c.soc_pct[peakIndex]}
          />
          <div className="panel-footnote">
            Maximum grid import ·{" "}
            {new Date(t[peakIndex]).toLocaleString("en-GB", {
              day: "numeric",
              month: "short",
              hour: "2-digit",
              minute: "2-digit",
              timeZone: "UTC",
            })}{" "}
            UTC
          </div>
        </Panel>
        <Panel title="Every megawatt-hour matters" eyebrow="RENEWABLE RECOVERY">
          <div className="recovery-value">
            {format(recovery)}
            <span>%</span>
            <small>of baseline surplus recovered</small>
          </div>
          <div className="recovery-bar">
            <span
              style={{ width: `${Math.max(0, Math.min(100, recovery))}%` }}
            />
          </div>
          <div className="stat-row">
            <span>Baseline surplus</span>
            <b>{format(m.baseline_curtailment_mwh, 0)} MWh</b>
          </div>
          <div className="stat-row">
            <span>Remaining surplus</span>
            <b>{format(m.curtailed_renewable_mwh, 0)} MWh</b>
          </div>
          <button
            className="text-button"
            onClick={() => onNavigate("scenarios")}
          >
            Explore a better configuration <MoveUpRight size={15} />
          </button>
        </Panel>
      </div>
    </>
  );
}
