import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  BatteryCharging,
  BookOpen,
  Check,
  ChevronDown,
  Command,
  FlaskConical,
  Gauge,
  Layers,
  LayoutDashboard,
  Menu,
  Play,
  Plus,
  Search,
  Share2,
  Shield,
  SlidersHorizontal,
  ChartNoAxesCombined,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { download, useResource } from "./api";
import { Slider, Status } from "./components/UI";
import { defaults, format, profiles, provenance, validSettings } from "./types";
import type { Settings, Simulation, Snapshot, View } from "./types";
import Overview from "./views/Overview";
const Dispatch = lazy(() => import("./views/Dispatch"));
const Scenarios = lazy(() => import("./views/Scenarios"));
const Forecast = lazy(() => import("./views/Forecast"));
const Stress = lazy(() => import("./views/Stress"));
const Optimizer = lazy(() => import("./views/Optimizer"));
const Methodology = lazy(() => import("./views/Methodology"));
const navigation = [
  { id: "overview", name: "Overview", icon: LayoutDashboard },
  { id: "dispatch", name: "Dispatch replay", icon: Activity },
  { id: "scenarios", name: "Scenario lab", icon: FlaskConical },
  { id: "forecast", name: "Forecasting", icon: ChartNoAxesCombined },
  { id: "stress", name: "Stress test", icon: Shield },
  { id: "optimizer", name: "Optimizer", icon: Gauge },
] as const;
function initialSettings(): Settings {
  try {
    const parsed = JSON.parse(
      new URLSearchParams(location.search).get("scenario") || "null",
    );
    if (validSettings(parsed))
      return Object.fromEntries(
        Object.keys(defaults).map((k) => [k, parsed[k as keyof Settings]]),
      ) as Settings;
  } catch {
    /* Use deterministic defaults for invalid links. */
  }
  return defaults;
}
function readSnapshots(): Snapshot[] {
  try {
    const value: unknown = JSON.parse(
      localStorage.getItem("gridflex.snapshots.v1") || "[]",
    );
    if (Array.isArray(value))
      return value
        .filter(
          (v): v is Snapshot =>
            v &&
            typeof v.id === "string" &&
            typeof v.name === "string" &&
            typeof v.savedAt === "string" &&
            validSettings(v.settings) &&
            v.metrics &&
            ["optimized_peak_mw", "renewable_utilization_pct"].every(
              (k) =>
                typeof v.metrics[k] === "number" &&
                Number.isFinite(v.metrics[k]),
            ),
        )
        .slice(0, 6);
  } catch {
    /* Browser storage can be disabled. */
  }
  return [];
}
export default function App() {
  const [active, setActive] = useState<Settings>(initialSettings);
  const [draft, setDraft] = useState(active);
  const [view, setView] = useState<View>("overview");
  const [snapshots, setSnapshots] = useState<Snapshot[]>(readSnapshots);
  const [notice, setNotice] = useState("");
  const [controls, setControls] = useState(false);
  const [menu, setMenu] = useState(false);
  const [mobile, setMobile] = useState(
    () => window.matchMedia("(max-width: 600px)").matches,
  );
  const [search, setSearch] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const result = useResource<Simulation>("simulate", active);
  const pending = JSON.stringify(active) !== JSON.stringify(draft);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 600px)");
    const onChange = () => setMobile(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        dialog.current?.showModal();
      }
    };
    document.addEventListener("keydown", listener);
    return () => document.removeEventListener("keydown", listener);
  }, []);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 4500);
    return () => clearTimeout(timer);
  }, [notice]);
  const update = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    setDraft((s) => ({ ...s, [key]: value }));
  function navigate(next: View) {
    setView(next);
    setMenu(false);
    dialog.current?.close();
  }
  function persist(next: Snapshot[]) {
    try {
      localStorage.setItem("gridflex.snapshots.v1", JSON.stringify(next));
      setSnapshots(next);
      return true;
    } catch {
      setNotice(
        "Browser storage is unavailable. Export the scenario to keep a copy.",
      );
      return false;
    }
  }
  function save() {
    if (!result.data || snapshots.length >= 6) return;
    const next = {
      id: crypto.randomUUID(),
      name: `${profiles[active.profile]} · ${active.duration_h}h / ${active.flexibility_pct}% flex`,
      savedAt: new Date().toISOString(),
      settings: active,
      metrics: result.data.metrics,
    };
    if (persist([...snapshots, next]))
      setNotice("Snapshot saved on this device.");
  }
  function exportRun() {
    if (!result.data) return;
    const { series, ...summary } = result.data;
    download(
      `gridflex-${summary.id}.json`,
      JSON.stringify(
        {
          ...summary,
          provenance: provenance[active.profile],
          exported_at: new Date().toISOString(),
        },
        null,
        2,
      ),
    );
    setNotice("Scenario settings and results exported.");
  }
  async function share() {
    const url = new URL(location.href);
    url.searchParams.set("scenario", JSON.stringify(active));
    try {
      await navigator.clipboard.writeText(url.toString());
      setNotice(
        "Scenario link copied. The recipient needs access to this app address.",
      );
    } catch {
      setNotice("Clipboard unavailable. Use Export to share these settings.");
    }
  }
  function preset(kind: "balanced" | "renewables" | "storage") {
    const s = {
      ...draft,
      ...(kind === "balanced"
        ? {
            penetration_pct: 90,
            flexibility_pct: 10,
            power_pct: 15,
            duration_h: 4,
          }
        : kind === "renewables"
          ? {
              penetration_pct: 130,
              flexibility_pct: 20,
              power_pct: 20,
              duration_h: 6,
            }
          : {
              penetration_pct: 100,
              flexibility_pct: 5,
              power_pct: 30,
              duration_h: 8,
            }),
    };
    setDraft(s);
    setActive(s);
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <aside
        className={`sidebar ${menu ? "mobile-open" : ""}`}
        inert={mobile && !menu}
      >
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("overview");
          }}
        >
          <span className="brand-icon">
            <Zap fill="currentColor" size={22} />
          </span>
          gridflex
        </a>
        <div className="workspace-label">
          <span>ENERGY WORKSPACE</span>
          <span>02</span>
        </div>
        <button
          className="search-button"
          onClick={() => dialog.current?.showModal()}
        >
          <Search size={15} />
          Quick navigation<kbd>⌘ K</kbd>
        </button>
        <div className="nav-label">LABORATORY</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ id, name, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item ${view === id ? "selected" : ""}`}
              aria-current={view === id ? "page" : undefined}
              onClick={() => navigate(id)}
            >
              <Icon size={18} />
              {name}
              {id === "scenarios" && <span className="new-tag">20</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-divider" />
        <div className="nav-label saved-label">
          SAVED SCENARIOS <span>{snapshots.length}/6</span>
        </div>
        <div className="saved-list">
          {snapshots.length === 0 ? (
            <p className="empty-saved">
              No saved scenarios.
              <br />
              Save a run to compare it later.
            </p>
          ) : (
            snapshots.map((s) => (
              <div className="saved-row" key={s.id}>
                <button
                  onClick={() => {
                    setDraft(s.settings);
                    setActive(s.settings);
                    navigate("overview");
                    setNotice("Saved scenario restored.");
                  }}
                  title={s.name}
                >
                  <Layers size={14} />
                  <span>{s.name}</span>
                </button>
                <button
                  className="delete-snapshot"
                  aria-label={`Delete ${s.name}`}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Delete this saved snapshot from this device?",
                      )
                    )
                      persist(snapshots.filter((v) => v.id !== s.id));
                  }}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))
          )}
        </div>
        <button
          className="save-sidebar"
          onClick={save}
          disabled={!result.data || pending || snapshots.length >= 6}
        >
          <Plus size={15} />
          Save current scenario
        </button>
        <div className="sidebar-bottom">
          <div className="research-note">
            <BookOpen size={20} />
            <strong>Model assumptions</strong>
            <p>
              Data sources and physical constraints.
              <br />
              Review the equations and limitations.
            </p>
            <button onClick={() => navigate("methodology")}>
              Read the methodology <ArrowRight size={14} />
            </button>
          </div>
          <div className="engine-status">
            <span />
            Simulation engine <b>v0.2</b>
          </div>
        </div>
      </aside>
      {menu && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="app-content">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMenu((v) => !v)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <span className="crumb-slash">/</span>
            <strong>
              {navigation.find((n) => n.id === view)?.name || "Methodology"}
            </strong>
            <span className="simulation-tag">SIMULATION</span>
          </div>
          <div className="top-actions">
            <button
              className="icon-button"
              aria-label="Share scenario"
              onClick={share}
            >
              <Share2 size={17} />
            </button>
            <button
              className="button export-button"
              onClick={exportRun}
              disabled={!result.data || pending}
            >
              <ArrowDownToLine size={15} />
              Export run
            </button>
            <button
              className="avatar"
              aria-label="Open methodology"
              onClick={() => navigate("methodology")}
            >
              GF
            </button>
          </div>
        </header>
        <div className="workspace-layout">
          <main id="workspace" className="workspace">
            <div className="page-heading">
              <div>
                <div className="eyebrow location-label">
                  <span />
                  {profiles[active.profile]}{" "}
                  <span className="heading-separator">/</span> {active.days}-DAY
                  HORIZON
                </div>
                <h1>
                  {
                    {
                      overview: "System overview",
                      dispatch: "Hourly dispatch",
                      scenarios: "Compare scenarios",
                      forecast: "Demand forecasting",
                      stress: "System stress test",
                      optimizer: "Dispatch optimization",
                      methodology: "Methodology",
                    }[view]
                  }
                </h1>
                <p>
                  {
                    {
                      overview:
                        "Measure the effect of storage and flexible demand on your selected profile.",
                      dispatch:
                        "Inspect hourly generation, demand, battery flows and grid import.",
                      scenarios:
                        "Compare storage duration and demand flexibility across 20 configurations.",
                      forecast:
                        "A chronological benchmark. No future observations in training.",
                      stress:
                        "Measure the effect of higher evening demand and lower renewable output.",
                      optimizer:
                        "Compare rule-based dispatch with a perfect-foresight optimization benchmark.",
                      methodology:
                        "Data sources, equations, assumptions and limits.",
                    }[view]
                  }
                </p>
              </div>
              <button
                className="button controls-toggle"
                onClick={() => setControls((v) => !v)}
              >
                <SlidersHorizontal size={16} />
                Configure
              </button>
            </div>
            <div className="run-context">
              <span className={`run-state ${result.loading ? "working" : ""}`}>
                <i />
                {result.loading
                  ? "Computing"
                  : result.error
                    ? "Run unavailable"
                    : pending
                      ? "Unapplied changes"
                      : "Simulation ready"}
              </span>
              <span>
                {provenance[active.profile]}
                {result.data &&
                  result.data.data_quality.imputed_hours > 0 &&
                  ` · ${result.data.data_quality.imputed_hours} missing hours interpolated`}
              </span>
            </div>
            {pending && (
              <div className="pending-banner">
                Controls changed. Results still show the last completed
                configuration.
                <button onClick={() => setActive(draft)}>
                  Run updated scenario <ArrowRight size={14} />
                </button>
              </div>
            )}
            {view === "methodology" ? (
              <Suspense fallback={<Status loading />}>
                <Methodology />
              </Suspense>
            ) : (
              <>
                <Status {...result} />
                {result.data && (
                  <Suspense fallback={<Status loading />}>
                    {view === "overview" && (
                      <Overview data={result.data} onNavigate={navigate} />
                    )}
                    {view === "dispatch" && (
                      <Dispatch key={result.data.id} data={result.data} />
                    )}
                    {view === "scenarios" && (
                      <Scenarios
                        data={result.data}
                        snapshots={snapshots}
                        onApply={(s) => {
                          setDraft(s);
                          setActive(s);
                          navigate("overview");
                        }}
                      />
                    )}
                    {view === "forecast" && <Forecast settings={active} />}
                    {view === "stress" && (
                      <Stress key={result.data.id} data={result.data} />
                    )}
                    {view === "optimizer" && (
                      <Optimizer key={result.data.id} data={result.data} />
                    )}
                  </Suspense>
                )}
              </>
            )}
            <footer className="workspace-footer">
              <span>GridFlex / Renewable power systems laboratory</span>
              <span>
                Research simulation · Not an operational grid controller
              </span>
            </footer>
          </main>
          <aside
            className={`controls-panel ${controls ? "open" : ""}`}
            aria-label="Scenario configuration"
          >
            <div className="controls-title">
              <span>
                <SlidersHorizontal size={16} />
                Scenario controls
              </span>
              <button
                className="icon-button controls-close"
                aria-label="Close controls"
                onClick={() => setControls(false)}
              >
                <X size={17} />
              </button>
              <span className="control-dot" />
            </div>
            <div className="control-section">
              <label className="field-label" htmlFor="profile">
                INPUT PROFILE
              </label>
              <div className="select-wrap">
                <select
                  id="profile"
                  value={draft.profile}
                  onChange={(e) =>
                    update("profile", e.target.value as Settings["profile"])
                  }
                >
                  {Object.entries(profiles).map(([v, name]) => (
                    <option key={v} value={v}>
                      {name}
                    </option>
                  ))}
                </select>
                <ChevronDown size={15} />
              </div>
              <label className="field-label horizon-label">
                ANALYSIS HORIZON
              </label>
              <div className="segmented">
                {([7, 14, 30, 60] as const).map((day) => (
                  <button
                    key={day}
                    className={draft.days === day ? "active" : ""}
                    onClick={() => update("days", day)}
                  >
                    {day}d
                  </button>
                ))}
              </div>
            </div>
            <div className="control-section">
              <h3>
                <Zap size={15} />
                Generation
              </h3>
              <Slider
                label="Renewable penetration"
                value={draft.penetration_pct}
                min={0}
                max={150}
                step={5}
                unit="%"
                onChange={(v) => update("penetration_pct", v)}
                hint="Renewable energy as a share of total demand."
              />
            </div>
            <div className="control-section">
              <h3>
                <BatteryCharging size={16} />
                Battery storage
              </h3>
              <Slider
                label="Power / mean demand"
                value={draft.power_pct}
                min={1}
                max={50}
                unit="%"
                onChange={(v) => update("power_pct", v)}
              />
              <Slider
                label="Storage duration"
                value={draft.duration_h}
                min={0}
                max={12}
                unit="h"
                onChange={(v) => update("duration_h", v)}
              />
              <Slider
                label="Round-trip efficiency"
                value={draft.efficiency_pct}
                min={50}
                max={100}
                unit="%"
                onChange={(v) => update("efficiency_pct", v)}
              />
              {result.data && (
                <div className="battery-summary">
                  <span>Applied battery</span>
                  <strong>
                    {active.duration_h
                      ? `${format(result.data.battery.max_charge_mw)} MW / ${format(result.data.battery.capacity_mwh)} MWh`
                      : "No storage"}
                  </strong>
                </div>
              )}
            </div>
            <div className="control-section">
              <h3>
                <Activity size={15} />
                Demand flexibility
              </h3>
              <Slider
                label="Shiftable share"
                value={draft.flexibility_pct}
                min={0}
                max={30}
                unit="%"
                onChange={(v) => update("flexibility_pct", v)}
                hint="Moved from high-load hours within each day."
              />
              <Slider
                label="Peak target percentile"
                value={draft.peak_quantile * 100}
                min={50}
                max={95}
                unit="%"
                onChange={(v) => update("peak_quantile", v / 100)}
              />
            </div>
            <button
              className="run-button"
              onClick={() => {
                setActive(draft);
                setControls(false);
                if (!pending) result.retry();
              }}
              disabled={result.loading}
            >
              <Play size={16} fill="currentColor" />
              {result.loading ? "Computing…" : "Run scenario"}
              <ArrowRight size={15} />
            </button>
            <div className="preset-heading">QUICK EXPERIMENTS</div>
            <div className="presets">
              <button onClick={() => preset("balanced")}>Balanced</button>
              <button onClick={() => preset("renewables")}>
                Surplus-heavy
              </button>
              <button onClick={() => preset("storage")}>Storage-first</button>
            </div>
            <p className="control-footnote">
              No API keys. No uploaded private data.
              <br />
              Deterministic, inspectable results.
            </p>
          </aside>
        </div>
      </div>
      {notice && (
        <div className="toast" role="status">
          <Check size={17} />
          {notice}
          <button
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={14} />
          </button>
        </div>
      )}
      <dialog
        ref={dialog}
        className="command-dialog"
        onClick={(e) => {
          if (e.target === e.currentTarget) dialog.current?.close();
        }}
      >
        <div className="command-head">
          <Command size={19} />
          <input
            aria-label="Search workspace views"
            placeholder="Where would you like to go?"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button
            className="icon-button"
            aria-label="Close quick navigation"
            onClick={() => dialog.current?.close()}
          >
            <X size={17} />
          </button>
        </div>
        <div className="command-results">
          {navigation
            .filter((n) => n.name.toLowerCase().includes(search.toLowerCase()))
            .map(({ id, name, icon: Icon }) => (
              <button key={id} onClick={() => navigate(id)}>
                <Icon size={18} />
                {name}
                <ArrowRight size={16} />
              </button>
            ))}
        </div>
      </dialog>
    </div>
  );
}
