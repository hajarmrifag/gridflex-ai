import { useEffect, useState } from "react";
import {
  ArrowDownToLine,
  Pause,
  Play,
  SkipBack,
  SkipForward,
} from "lucide-react";
import { Chart, Legend } from "../components/Chart";
import { EnergyFlow } from "../components/EnergyFlow";
import { Panel } from "../components/UI";
import { download } from "../api";
import { format } from "../types";
import type { Simulation } from "../types";
export default function Dispatch({ data }: { data: Simulation }) {
  const [hour, setHour] = useState(12);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const { timestamps: t, columns: c } = data.series;
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(
      () => setHour((v) => (v + 1) % t.length),
      700 / speed,
    );
    return () => clearInterval(timer);
  }, [playing, speed, t.length]);
  const start = Math.floor(hour / 24) * 24,
    end = Math.min(t.length, start + 24);
  const lines = [
    {
      name: "Net grid load",
      values: c.optimized_net_load_mw.slice(start, end),
      color: "#279279",
      fill: true,
    },
    {
      name: "Battery discharge",
      values: c.battery_discharge_mw.slice(start, end),
      color: "#d59b35",
    },
    {
      name: "Battery charging",
      values: c.battery_charge_mw.slice(start, end).map((v) => -v),
      color: "#6086c2",
    },
  ];
  function exportCSV() {
    const keys = Object.keys(c);
    download(
      `gridflex-dispatch-${data.id}.csv`,
      [
        "timestamp," + keys.join(","),
        ...t.map((stamp, i) => [stamp, ...keys.map((k) => c[k][i])].join(",")),
      ].join("\n"),
      "text/csv",
    );
  }
  return (
    <>
      <Panel
        title={
          new Date(t[hour]).toLocaleString("en-GB", {
            weekday: "long",
            day: "numeric",
            month: "long",
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "UTC",
          }) + " UTC"
        }
        eyebrow="HOURLY DISPATCH REPLAY"
        className="replay-panel"
        action={
          <span className="pill">
            Hour {hour + 1} / {t.length}
          </span>
        }
      >
        <EnergyFlow
          solar={c.solar_mw[hour]}
          wind={c.wind_mw[hour]}
          demand={c.demand_mw[hour]}
          charge={c.battery_charge_mw[hour]}
          discharge={c.battery_discharge_mw[hour]}
          net={c.optimized_net_load_mw[hour]}
          soc={c.soc_pct[hour]}
        />
        <div className="replay-controls">
          <button
            className="icon-button"
            aria-label="Previous hour"
            onClick={() => setHour((v) => Math.max(0, v - 1))}
          >
            <SkipBack size={18} />
          </button>
          <button
            className="play-button"
            aria-label={playing ? "Pause replay" : "Play replay"}
            onClick={() => setPlaying((v) => !v)}
          >
            {playing ? (
              <Pause size={18} />
            ) : (
              <Play size={18} fill="currentColor" />
            )}
          </button>
          <button
            className="icon-button"
            aria-label="Next hour"
            onClick={() => setHour((v) => Math.min(t.length - 1, v + 1))}
          >
            <SkipForward size={18} />
          </button>
          <input
            aria-label="Replay hour"
            type="range"
            min={0}
            max={t.length - 1}
            value={hour}
            onChange={(e) => {
              setPlaying(false);
              setHour(Number(e.target.value));
            }}
          />
          <select
            aria-label="Replay speed"
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
          >
            <option value={1}>1×</option>
            <option value={2}>2×</option>
            <option value={4}>4×</option>
          </select>
        </div>
      </Panel>
      <div className="replay-stats">
        <div>
          <span>State of charge</span>
          <strong>{format(c.soc_pct[hour])}%</strong>
          <div className="mini-track">
            <i style={{ width: `${c.soc_pct[hour]}%` }} />
          </div>
        </div>
        <div>
          <span>Demand shifted</span>
          <strong>{format(c.demand_shift_mw[hour])} MW</strong>
          <small>Negative = moved away from this hour</small>
        </div>
        <div>
          <span>Fixed dispatch target</span>
          <strong>{format(data.peak_target_mw)} MW</strong>
          <small>Discharge only above this threshold</small>
        </div>
      </div>
      <Panel
        title="One day, in detail"
        eyebrow="POWER BALANCE"
        action={
          <button className="button" onClick={exportCSV}>
            <ArrowDownToLine size={15} />
            Download all hours
          </button>
        }
      >
        <Chart
          lines={lines}
          timestamps={t.slice(start, end)}
          cursor={hour - start}
        />
        <Legend lines={lines} />
      </Panel>
      <Panel title="Stored energy through the horizon">
        <Chart
          lines={[
            {
              name: "State of charge",
              values: c.soc_pct,
              color: "#279279",
              fill: true,
            },
          ]}
          timestamps={t}
          cursor={hour}
          unit="%"
          label="Battery state of charge"
          height={180}
        />
      </Panel>
    </>
  );
}
