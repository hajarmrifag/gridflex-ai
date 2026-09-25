import { useState } from "react";
import { ArrowDownToLine, ArrowUpRight, Layers } from "lucide-react";
import { download, useResource } from "../api";
import { Panel, Status } from "../components/UI";
import { format } from "../types";
import type { Metrics, Settings, Simulation, Snapshot } from "../types";
type Row = Metrics & {
  duration_h: number;
  flexibility_pct: number;
  capacity_mwh: number;
  power_mw: number;
};
export default function Scenarios({
  data,
  snapshots,
  onApply,
}: {
  data: Simulation;
  snapshots: Snapshot[];
  onApply: (s: Settings) => void;
}) {
  const result = useResource<{ scenarios: Row[] }>("compare", data.settings);
  const [measure, setMeasure] = useState("peak_reduction_pct");
  const [selected, setSelected] = useState<Row>();
  const rows = result.data?.scenarios || [];
  const max = Math.max(1, ...rows.map((r) => r[measure])),
    min = Math.min(0, ...rows.map((r) => r[measure]));
  function exportCSV() {
    const keys = Object.keys(rows[0]);
    download(
      "gridflex-sizing-comparison.csv",
      [
        keys.join(","),
        ...rows.map((r) => keys.map((k) => r[k]).join(",")),
      ].join("\n"),
      "text/csv",
    );
  }
  return (
    <>
      <Status {...result} />
      {result.data && (
        <>
          <Panel
            title="20 ways to balance your system"
            eyebrow="STORAGE × FLEXIBILITY"
            action={
              <select
                aria-label="Comparison metric"
                value={measure}
                onChange={(e) => setMeasure(e.target.value)}
              >
                <option value="peak_reduction_pct">Peak reduction (%)</option>
                <option value="renewable_utilization_pct">
                  Renewable utilisation (%)
                </option>
                <option value="curtailment_avoided_mwh">
                  Surplus recovered (MWh)
                </option>
              </select>
            }
          >
            <p className="panel-description">
              Same generation profile. Same battery power. Select a cell to
              inspect and apply its configuration.
            </p>
            <div className="heatmap-scroll">
              <div className="heatmap">
                <div className="heatmap-axis">FLEX / STORAGE</div>
                {[0, 2, 4, 8].map((h) => (
                  <div className="heatmap-col" key={h}>
                    {h === 0 ? "No storage" : `${h} hours`}
                  </div>
                ))}
                {[0, 5, 10, 15, 20].map((f) => (
                  <div className="heatmap-row" key={f}>
                    <div className="heatmap-label">{f}% flex</div>
                    {[0, 2, 4, 8].map((h) => {
                      const row = rows.find(
                        (r) => r.duration_h === h && r.flexibility_pct === f,
                      )!;
                      const intensity = (row[measure] - min) / (max - min);
                      return (
                        <button
                          key={h}
                          className={`heat-cell ${selected === row ? "selected" : ""}`}
                          style={{
                            background: `hsl(137 30% ${96 - intensity * 64}%)`,
                            color: intensity > 0.6 ? "#fff" : "#20442c",
                          }}
                          aria-label={`${h} hours storage, ${f} percent flexibility: ${format(row[measure])}`}
                          onClick={() => setSelected(row)}
                        >
                          <strong>{format(row[measure])}</strong>
                          <span>{measure.endsWith("pct") ? "%" : "MWh"}</span>
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
            <div className="heatmap-footer">
              <span>
                Less impact <i /> More impact
              </span>
              <button className="text-button" onClick={exportCSV}>
                <ArrowDownToLine size={14} />
                Export 20 scenarios
              </button>
            </div>
            {selected ? (
              <div className="scenario-selection">
                <div>
                  <strong>
                    {selected.duration_h}h storage + {selected.flexibility_pct}%
                    flexibility
                  </strong>
                  <span>
                    {format(selected.capacity_mwh)} MWh ·{" "}
                    {format(selected.power_mw)} MW · Peak reduction{" "}
                    {format(selected.peak_reduction_pct)}%
                  </span>
                </div>
                <button
                  className="button primary"
                  onClick={() =>
                    onApply({
                      ...data.settings,
                      duration_h: selected.duration_h,
                      flexibility_pct: selected.flexibility_pct,
                    })
                  }
                >
                  Use this scenario <ArrowUpRight size={16} />
                </button>
              </div>
            ) : (
              <div className="callout">
                0 hours is an exact no-storage baseline. Larger demand shifts
                can create new peaks; benefits are not guaranteed to increase.
              </div>
            )}
          </Panel>
          <Panel
            title="Your experiments, side by side"
            eyebrow="SAVED ON THIS DEVICE"
            action={<Layers size={19} />}
          >
            {snapshots.length === 0 ? (
              <div className="empty-state">
                <Layers size={26} />
                <h3>Keep a result worth comparing.</h3>
                <p>
                  Save scenarios from the sidebar to compare their peak import
                  and renewable utilisation here.
                </p>
              </div>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Scenario</th>
                      <th>Peak import</th>
                      <th>Renewables used</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>
                        <b>Current run</b>
                      </td>
                      <td>{format(data.metrics.optimized_peak_mw)} MW</td>
                      <td>{format(data.metrics.renewable_utilization_pct)}%</td>
                      <td />
                    </tr>
                    {snapshots.map((s) => (
                      <tr key={s.id}>
                        <td>
                          {s.name}
                          <small>
                            {s.settings.days} days ·{" "}
                            {s.settings.penetration_pct}% renewables
                          </small>
                        </td>
                        <td>{format(s.metrics.optimized_peak_mw)} MW</td>
                        <td>{format(s.metrics.renewable_utilization_pct)}%</td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() => onApply(s.settings)}
                          >
                            Restore
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="panel-description">
                  Compare like-for-like profiles and horizons; city and national
                  power levels are not directly comparable.
                </p>
              </div>
            )}
          </Panel>
        </>
      )}
    </>
  );
}
