import { Chart, Legend } from "../components/Chart";
import { Panel, Status } from "../components/UI";
import { useResource } from "../api";
import { format } from "../types";
import type { Series, Settings } from "../types";
export default function Forecast({ settings }: { settings: Settings }) {
  const result = useResource<{
    series: Series;
    metrics: Record<string, number | null>;
  }>("forecast", settings);
  if (settings.days < 9)
    return (
      <Panel title="Give the model a little more history">
        <div className="empty-state">
          <h3>Weekly patterns need more than a week.</h3>
          <p>
            Select a 14-day or longer horizon and run the scenario. The model
            uses 24-hour and 168-hour demand lags.
          </p>
        </div>
      </Panel>
    );
  const d = result.data;
  const lines = d
    ? [
        {
          name: "Actual demand",
          values: d.series.columns.actual_mw,
          color: "#2b3930",
        },
        {
          name: "Gradient boosting",
          values: d.series.columns.forecast_mw,
          color: "#329b78",
        },
        {
          name: "24h persistence",
          values: d.series.columns.day_ahead_naive_mw,
          color: "#c8a057",
          dashed: true,
        },
      ]
    : [];
  return (
    <>
      <Status {...result} />
      {d && (
        <>
          <div className="replay-stats">
            <div>
              <span>Model mean absolute error</span>
              <strong>{format(d.metrics.model_mae_mw!)} MW</strong>
              <small>Lower is better</small>
            </div>
            <div>
              <span>Persistence baseline error</span>
              <strong>{format(d.metrics.naive_mae_mw!)} MW</strong>
              <small>Yesterday’s demand at the same hour</small>
            </div>
            <div>
              <span>Improvement over persistence</span>
              <strong>
                {d.metrics.improvement_vs_naive_pct === null
                  ? "N/A"
                  : `${format(d.metrics.improvement_vs_naive_pct)}%`}
              </strong>
              <small>Negative means the baseline wins</small>
            </div>
          </div>
          <Panel
            title="Predictions meet observations"
            eyebrow="CHRONOLOGICAL HOLDOUT"
          >
            <Chart
              lines={lines}
              timestamps={d.series.timestamps}
              height={330}
            />
            <Legend lines={lines} />
          </Panel>
          <div className="two-column">
            <Panel title="A fair test">
              <p className="prose">
                The model trains on the first 80% of usable observations. The
                final 20% is held out. Each prediction uses calendar features
                and observed demand from 24 and 168 hours earlier.
              </p>
            </Panel>
            <Panel title="What this doesn’t prove">
              <p className="prose">
                This is a rolling day-ahead benchmark with observed lag updates,
                not a single forecast of the entire future horizon. Demand
                forecasts do not drive the dispatch controller.
              </p>
            </Panel>
          </div>
        </>
      )}
    </>
  );
}
