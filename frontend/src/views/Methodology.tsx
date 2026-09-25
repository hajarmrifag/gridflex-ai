import {
  BatteryCharging,
  Database,
  FlaskConical,
  Scale,
  ShieldCheck,
  Waves,
} from "lucide-react";
import { Panel } from "../components/UI";
export default function Methodology() {
  return (
    <>
      <div className="method-intro">
        <ShieldCheck size={32} />
        <div>
          <h2>Every headline traces back to an hourly power balance.</h2>
          <p>
            GridFlex is a research laboratory for battery storage and flexible
            demand. These are simulations, not grid-control instructions or
            investment recommendations.
          </p>
        </div>
      </div>
      <div className="method-grid">
        {[
          {
            icon: Database,
            title: "Know your data",
            text: "Germany uses measured demand, solar and wind from OPSD. Tétouan uses measured city demand and renewable profiles estimated from local weather. Synthetic mode is deterministic, seeded test data.",
          },
          {
            icon: Waves,
            title: "Conserve energy",
            text: "Flexible demand moves within each day from the highest to the lowest residual-load quartile. Total daily demand energy stays unchanged. Equal quartiles are left alone; larger shifts can create new peaks.",
          },
          {
            icon: BatteryCharging,
            title: "Respect physical limits",
            text: "Battery capacity, power, reserve, state of charge and conversion losses are explicit. Charging happens only from surplus; discharging begins above a fixed target. Zero storage disables both charge and discharge.",
          },
          {
            icon: FlaskConical,
            title: "Separate foresight from control",
            text: "The battery rule uses current state. Daily load shifting and the chosen threshold use the historical scenario, so the full experiment is retrospective. The LP sees the entire future horizon and is labeled accordingly.",
          },
          {
            icon: Scale,
            title: "Compare like for like",
            text: "Battery power is a share of mean demand. Duration sets energy capacity. This gives national and city-scale profiles comparable relative sizing. Stress scenarios hold installed renewable capacity and the dispatch target fixed.",
          },
          {
            icon: ShieldCheck,
            title: "Make limits visible",
            text: "No transmission network, prices, unit commitment, degradation model or outage probabilities. Residual surplus is a curtailment proxy. Stored energy at the start is not free generation; both controllers can finish below starting charge unless constrained.",
          },
        ].map(({ icon: Icon, title, text }) => (
          <Panel key={title} title={title} action={<Icon size={20} />}>
            <p className="prose">{text}</p>
          </Panel>
        ))}
      </div>
      <Panel
        title="The core accounting identity"
        eyebrow="MW AT EVERY TIME STEP"
      >
        <div className="equation">
          Grid load = Demand − Renewables + Charging − Discharging
        </div>
        <p className="panel-description">
          Positive is grid import. Negative is renewable surplus.
          Charge/discharge losses use symmetric efficiencies whose product
          equals round-trip efficiency.
        </p>
      </Panel>
      <div className="method-links">
        <a
          href="https://github.com/hajarmrifag/gridflex-ai"
          target="_blank"
          rel="noreferrer"
        >
          Source repository ↗
        </a>
        <a
          href="https://github.com/hajarmrifag/gridflex-ai/blob/main/data/README.md"
          target="_blank"
          rel="noreferrer"
        >
          Data provenance ↗
        </a>
        <a href="/api/docs" target="_blank" rel="noreferrer">
          Simulation API ↗
        </a>
      </div>
    </>
  );
}
