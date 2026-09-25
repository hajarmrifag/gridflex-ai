import { useState } from "react";
import { Play, Shield } from "lucide-react";
import { useResource } from "../api";
import { Chart, Legend } from "../components/Chart";
import { Panel, Slider, Status } from "../components/UI";
import { format } from "../types";
import type { Metrics, Series, Simulation } from "../types";
export default function Stress({ data }: { data: Simulation }) {
  const [demand, setDemand] = useState(25),
    [drop, setDrop] = useState(40);
  const [stress, setStress] = useState({
    demand_shock_pct: 25,
    renewable_drop_pct: 40,
  });
  const result = useResource<{ series: Series; metrics: Metrics }>("stress", {
    ...data.settings,
    ...stress,
  });
  const d = result.data;
  const lines = d
    ? [
        {
          name: "Normal conditions",
          values: data.series.columns.optimized_net_load_mw,
          color: "#7c9c8a",
          dashed: true,
        },
        {
          name: "Stressed conditions",
          values: d.series.columns.optimized_net_load_mw,
          color: "#d58b44",
          fill: true,
        },
      ]
    : [];
  return (
    <>
      <Panel
        title="Change the conditions. Keep the physics."
        eyebrow="CONTROLLED STRESS EXPERIMENT"
        action={<Shield size={20} />}
      >
        <div className="stress-controls">
          <Slider
            label="Evening demand surge"
            min={0}
            max={100}
            value={demand}
            unit="%"
            onChange={setDemand}
            hint="17:00–21:00 in the profile’s time zone, every day."
          />
          <Slider
            label="Renewable generation loss"
            min={0}
            max={100}
            value={drop}
            unit="%"
            onChange={setDrop}
            hint="Solar and wind derated across the whole horizon."
          />
          <button
            className="button primary"
            onClick={() =>
              setStress({ demand_shock_pct: demand, renewable_drop_pct: drop })
            }
            disabled={result.loading}
          >
            <Play size={15} />
            Apply stress
          </button>
        </div>
      </Panel>
      <Status {...result} />
      {d && (
        <>
          <div className="replay-stats">
            <div>
              <span>Stressed peak import</span>
              <strong>{format(d.metrics.optimized_peak_mw)} MW</strong>
              <small>
                {format(
                  d.metrics.optimized_peak_mw - data.metrics.optimized_peak_mw,
                )}{" "}
                MW change from normal
              </small>
            </div>
            <div>
              <span>Stressed storage delivery</span>
              <strong>
                {format(d.metrics.energy_from_storage_mwh, 0)} MWh
              </strong>
              <small>
                {format(d.metrics.equivalent_battery_cycles)} equivalent cycles
              </small>
            </div>
            <div>
              <span>Remaining renewable utilisation</span>
              <strong>{format(d.metrics.renewable_utilization_pct)}%</strong>
              <small>Share of the reduced renewable supply</small>
            </div>
          </div>
          <Panel
            title="How much pressure can the system absorb?"
            eyebrow={`${stress.demand_shock_pct}% EVENING SURGE / ${stress.renewable_drop_pct}% GENERATION LOSS`}
          >
            <Chart
              lines={lines}
              timestamps={data.series.timestamps}
              height={330}
            />
            <Legend lines={lines} />
          </Panel>
          <div className="callout">
            Installed generation and the original dispatch target stay fixed.
            Demand shifting is recalculated under stress. This is a sensitivity
            experiment, not a grid-outage or reliability forecast.
          </div>
        </>
      )}
    </>
  );
}
