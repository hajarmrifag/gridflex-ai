import {
  AlertTriangle,
  ArrowUpRight,
  LoaderCircle,
  RotateCcw,
} from "lucide-react";
import type { ReactNode } from "react";
export function Panel({
  title,
  eyebrow,
  action,
  children,
  className = "",
}: {
  title: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-head">
        <div>
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Metric({
  label,
  value,
  unit,
  note,
  icon,
  accent = "green",
}: {
  label: string;
  value: string;
  unit?: string;
  note: string;
  icon: ReactNode;
  accent?: string;
}) {
  return (
    <div className={`metric ${accent}`}>
      <div className="metric-label">
        {label}
        <span>{icon}</span>
      </div>
      <div className="metric-value">
        {value}
        <small>{unit}</small>
      </div>
      <div className="metric-note">
        <ArrowUpRight size={13} />
        {note}
      </div>
    </div>
  );
}
export function Status({
  loading,
  error,
  retry,
}: {
  loading: boolean;
  error?: string;
  retry?: () => void;
}) {
  if (error)
    return (
      <div className="status error" role="alert">
        <AlertTriangle />
        <h3>We couldn’t complete that run</h3>
        <p>{error}</p>
        {retry && (
          <button className="button" onClick={retry}>
            <RotateCcw size={16} />
            Try again
          </button>
        )}
      </div>
    );
  if (loading)
    return (
      <div className="status" role="status">
        <LoaderCircle className="spin" />
        <h3>Running the experiment</h3>
        <p>Balancing every hour of your energy system.</p>
      </div>
    );
  return null;
}
export function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  onChange,
  hint,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (v: number) => void;
  hint?: string;
}) {
  return (
    <label className="slider-field">
      <span>
        {label}
        <b>
          {Number(value.toFixed(2))}
          {unit}
        </b>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      {hint && <small>{hint}</small>}
    </label>
  );
}
