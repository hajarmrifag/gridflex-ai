import { useId, useState } from "react";
import { format } from "../types";
export type Line = {
  name: string;
  values: number[];
  color: string;
  dashed?: boolean;
  fill?: boolean;
};
export function Chart({
  lines,
  timestamps,
  height = 260,
  dark = false,
  cursor,
  label = "Power over time",
  unit = "MW",
}: {
  lines: Line[];
  timestamps: string[];
  height?: number;
  dark?: boolean;
  cursor?: number;
  label?: string;
  unit?: string;
}) {
  const id = useId().replace(/:/g, "");
  const [hover, setHover] = useState<number | null>(null);
  const values = lines.flatMap((l) => l.values);
  const lo = Math.min(0, ...values),
    hi = Math.max(1, ...values);
  const range = hi - lo || 1;
  const n = Math.max(2, timestamps.length);
  const x = (i: number) => 54 + (i / (n - 1)) * 900;
  const y = (v: number) => 16 + ((hi - v) / range) * 210;
  const active = hover ?? cursor;
  const date = (i: number) =>
    new Date(timestamps[i]).toLocaleString("en-GB", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      timeZone: "UTC",
    });
  return (
    <div
      className={`chart ${dark ? "chart-dark" : ""}`}
      style={{ height }}
      onMouseLeave={() => setHover(null)}
    >
      <svg
        viewBox="0 0 1000 260"
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
        onPointerMove={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          setHover(
            Math.max(
              0,
              Math.min(
                timestamps.length - 1,
                Math.round(
                  ((((event.clientX - bounds.left) / bounds.width) * 1000 -
                    54) /
                    900) *
                    (n - 1),
                ),
              ),
            ),
          );
        }}
      >
        <title>{label}</title>
        <defs>
          {lines
            .filter((l) => l.fill)
            .map((l, i) => (
              <linearGradient
                key={l.name}
                id={`${id}-${i}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor={l.color} stopOpacity=".25" />
                <stop offset="100%" stopColor={l.color} stopOpacity="0" />
              </linearGradient>
            ))}
        </defs>
        {[0, 1, 2, 3, 4].map((i) => (
          <g key={i}>
            <line
              x1="54"
              x2="954"
              y1={16 + i * 52.5}
              y2={16 + i * 52.5}
              className="chart-grid"
            />
          </g>
        ))}
        {lo < 0 && (
          <line x1="54" x2="954" y1={y(0)} y2={y(0)} className="zero-line" />
        )}
        {lines.map((l, i) => {
          const path = l.values
            .map(
              (v, j) => `${j ? "L" : "M"}${x(j).toFixed(2)},${y(v).toFixed(2)}`,
            )
            .join(" ");
          return (
            <g key={l.name}>
              {l.fill && (
                <path
                  d={`${path} L${x(l.values.length - 1)},${y(0)} L54,${y(0)} Z`}
                  fill={`url(#${id}-${lines.slice(0, i).filter((v) => v.fill).length})`}
                />
              )}
              <path
                d={path}
                fill="none"
                stroke={l.color}
                strokeWidth="2.2"
                strokeDasharray={l.dashed ? "6 5" : undefined}
                vectorEffect="non-scaling-stroke"
              />
            </g>
          );
        })}
        {active !== undefined && active !== null && (
          <g>
            <line
              x1={x(active)}
              x2={x(active)}
              y1="16"
              y2="226"
              className="cursor-line"
            />
            {lines.map((l) => (
              <circle
                key={l.name}
                cx={x(active)}
                cy={y(l.values[active])}
                r="4"
                fill={l.color}
              />
            ))}
          </g>
        )}
      </svg>
      <div className="chart-labels" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="chart-y-label"
            style={{ top: `${((16 + i * 52.5) / 260) * 100}%` }}
          >
            {format(hi - (i * range) / 4, 0)}
          </span>
        ))}
        {[0, 0.25, 0.5, 0.75, 1].map((v) => {
          const i = Math.round(v * (timestamps.length - 1));
          return (
            <span
              key={v}
              className={`chart-x-label tick-${v}`}
              style={{ left: `${x(i) / 10}%` }}
            >
              {new Date(timestamps[i]).toLocaleString(
                "en-GB",
                timestamps.length <= 48
                  ? { hour: "2-digit", minute: "2-digit", timeZone: "UTC" }
                  : { month: "short", day: "numeric", timeZone: "UTC" },
              )}
            </span>
          );
        })}
      </div>
      {hover !== null && (
        <div className="chart-tooltip">
          <strong>{date(hover)} UTC</strong>
          {lines.map((l) => (
            <span key={l.name}>
              <i style={{ background: l.color }} />
              {l.name}
              <b>
                {format(l.values[hover])} {unit}
              </b>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
export function Legend({ lines }: { lines: Pick<Line, "name" | "color">[] }) {
  return (
    <div className="legend">
      {lines.map((l) => (
        <span key={l.name}>
          <i style={{ background: l.color }} />
          {l.name}
        </span>
      ))}
    </div>
  );
}
