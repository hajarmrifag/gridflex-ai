import { useState } from "react";
import { Gauge } from "lucide-react";
import { useResource } from "../api";
import { Chart, Legend } from "../components/Chart";
import { Panel, Status } from "../components/UI";
import { format } from "../types";
import type { Series, Simulation } from "../types";
export default function Optimizer({ data }: { data: Simulation }) {
  const [grid, setGrid] = useState(false),
    [restore, setRestore] = useState(false);
  const result = useResource<{
    series: Series;
    peak_mw: number;
    heuristic_peak_mw: number;
    optimality_tolerance_mw: number;
  }>("optimize", {
    ...data.settings,
    allow_grid_charging: grid,
    restore_soc: restore,
  });
  const d = result.data;
  const before = Math.max(0, ...data.series.columns.net_load_mw);
  const gain = d ? before - d.peak_mw : 0;
  const capture =
    d && gain > Math.max(1e-6, before * 0.005) && !restore
      ? (100 * (before - d.heuristic_peak_mw)) / gain
      : null;
  const lines = d
    ? [
        {
          name: "No battery",
          values: data.series.columns.net_load_mw,
          color: "#a5afa7",
          dashed: true,
        },
        {
          name: "Heuristic",
          values: data.series.columns.optimized_net_load_mw,
          color: "#338f72",
        },
        {
          name: "Perfect foresight",
          values: d.series.columns.lp_optimal_net_load_mw,
          color: "#ba9148",
        },
      ]
    : [];
  return (
    <>
      <Panel
        title="Define a fair comparison"
        eyebrow="PERFECT-FORESIGHT BENCHMARK"
        action={<Gauge size={20} />}
      >
        <div className="optimizer-options">
          <label>
            <input
              type="checkbox"
              checked={grid}
              onChange={(e) => setGrid(e.target.checked)}
            />
            <span>
              <b>Allow grid charging</b>
              <small>
                Off matches the heuristic’s surplus-only charging policy.
              </small>
            </span>
          </label>
          <label>
            <input
              type="checkbox"
              checked={restore}
              onChange={(e) => setRestore(e.target.checked)}
            />
            <span>
              <b>Restore initial state of charge</b>
              <small>Require at least 50% charge at the horizon’s end.</small>
            </span>
          </label>
        </div>
      </Panel>
      <Status {...result} />
      {d && (
        <>
          <div className="replay-stats">
            <div>
              <span>Heuristic peak import</span>
              <strong>{format(d.heuristic_peak_mw)} MW</strong>
              <small>The current threshold-based dispatch</small>
            </div>
            <div>
              <span>Perfect-foresight peak</span>
              <strong>{format(d.peak_mw)} MW</strong>
              <small>Peak first, then minimum battery cycling</small>
            </div>
            <div>
              <span>Achievable reduction captured</span>
              <strong>
                {capture === null ? "N/A" : `${format(capture, 0)}%`}
              </strong>
              <small>
                {restore
                  ? "Terminal constraints differ from the heuristic"
                  : gain <= Math.max(1e-6, before * 0.005)
                    ? "Battery contribution too small for a useful ratio"
                    : "Of the battery’s peak-reduction potential"}
              </small>
            </div>
          </div>
          <Panel title="The gap between a rule and foresight">
            <Chart
              lines={lines}
              timestamps={data.series.timestamps}
              height={330}
            />
            <Legend lines={lines} />
          </Panel>
          <div className="callout">
            The optimizer sees the entire horizon. It provides a theoretical
            bound, not a deployable real-time forecast.{" "}
            {restore
              ? "The end-charge requirement can be infeasible without enough charging energy."
              : "Both controllers may finish below their starting charge; initial stored energy is part of the experiment."}{" "}
            Numerical peak tolerance:{" "}
            {d.optimality_tolerance_mw.toExponential(1)} MW.
          </div>
        </>
      )}
    </>
  );
}
