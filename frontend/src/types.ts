export type View =
  | "overview"
  | "dispatch"
  | "scenarios"
  | "forecast"
  | "stress"
  | "optimizer"
  | "methodology";
export type Settings = {
  profile: "morocco" | "germany" | "synthetic";
  days: 7 | 14 | 30 | 60;
  penetration_pct: number;
  flexibility_pct: number;
  power_pct: number;
  duration_h: number;
  efficiency_pct: number;
  peak_quantile: number;
};
export type Series = {
  timestamps: string[];
  columns: Record<string, number[]>;
};
export type Metrics = Record<string, number>;
export type Simulation = {
  id: string;
  settings: Settings;
  battery: {
    capacity_mwh: number;
    max_charge_mw: number;
    round_trip_efficiency: number;
  };
  metrics: Metrics;
  series: Series;
  peak_target_mw: number;
  engine_version: string;
  data_quality: { imputed_hours: number; method: string };
};
export type Snapshot = {
  id: string;
  name: string;
  savedAt: string;
  settings: Settings;
  metrics: Metrics;
};
export const defaults: Settings = {
  profile: "morocco",
  days: 30,
  penetration_pct: 90,
  flexibility_pct: 10,
  power_pct: 15,
  duration_h: 4,
  efficiency_pct: 90,
  peak_quantile: 0.72,
};
export const profiles = {
  morocco: "Tétouan, Morocco",
  germany: "Germany",
  synthetic: "Synthetic system",
};
export const provenance = {
  morocco:
    "Measured Tétouan demand · renewables estimated from local weather · 2017",
  germany: "Historical German demand, wind & solar · Open Power System Data",
  synthetic: "Deterministic synthetic stress profile · seed 42 · June 2024",
};
export const format = (value: number, digits = 1) =>
  new Intl.NumberFormat("en", { maximumFractionDigits: digits }).format(value);
export function validSettings(value: unknown): value is Settings {
  if (!value || typeof value !== "object") return false;
  const s = value as Settings;
  return (
    ["morocco", "germany", "synthetic"].includes(s.profile) &&
    [7, 14, 30, 60].includes(s.days) &&
    Object.entries({
      penetration_pct: [0, 150],
      flexibility_pct: [0, 30],
      power_pct: [1, 50],
      duration_h: [0, 12],
      efficiency_pct: [50, 100],
      peak_quantile: [0.5, 0.95],
    }).every(
      ([key, [min, max]]) =>
        typeof s[key as keyof Settings] === "number" &&
        Number.isFinite(s[key as keyof Settings]) &&
        Number(s[key as keyof Settings]) >= min &&
        Number(s[key as keyof Settings]) <= max,
    )
  );
}
