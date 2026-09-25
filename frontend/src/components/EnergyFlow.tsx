import { BatteryCharging, Factory, Sun, UtilityPole, Wind } from "lucide-react";
import { format } from "../types";
export function EnergyFlow({
  solar,
  wind,
  demand,
  charge,
  discharge,
  net,
  soc,
}: {
  solar: number;
  wind: number;
  demand: number;
  charge: number;
  discharge: number;
  net: number;
  soc: number;
}) {
  const battery =
    charge > 0.001 ? "Charging" : discharge > 0.001 ? "Discharging" : "Holding";
  return (
    <div
      className="energy-flow"
      aria-label={`Solar ${format(solar)} MW, wind ${format(wind)} MW, demand ${format(demand)} MW, battery ${battery.toLowerCase()} at ${format(soc)} percent`}
    >
      <svg
        className="flow-wires"
        viewBox="0 0 720 200"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path d="M100 45H235Q260 45 260 70V100H360 M100 155H235Q260 155 260 130V100H360 M360 100H490Q520 100 520 70V45H620 M360 100H490Q520 100 520 130V155H620" />
        <path
          className="flow-current"
          d="M100 45H235Q260 45 260 70V100H360 M100 155H235Q260 155 260 130V100H360 M360 100H490Q520 100 520 70V45H620 M360 100H490Q520 100 520 130V155H620"
        />
      </svg>
      <div className="flow-side">
        <div className="flow-node solar">
          <Sun size={20} />
          <span>
            Solar
            <b>
              {format(solar)} <small>MW</small>
            </b>
          </span>
        </div>
        <div className="flow-node wind">
          <Wind size={20} />
          <span>
            Wind
            <b>
              {format(wind)} <small>MW</small>
            </b>
          </span>
        </div>
      </div>
      <div className="flow-battery">
        <div className="battery-orbit">
          <BatteryCharging size={30} />
        </div>
        <strong>
          {format(soc, 0)}
          <small>%</small>
        </strong>
        <span>
          {battery} · {format(Math.max(charge, discharge))} MW
        </span>
      </div>
      <div className="flow-side">
        <div className="flow-node demand">
          <Factory size={20} />
          <span>
            Demand
            <b>
              {format(demand)} <small>MW</small>
            </b>
          </span>
        </div>
        <div className="flow-node grid">
          <UtilityPole size={20} />
          <span>
            {net < 0 ? "Surplus" : "Grid import"}
            <b>
              {format(Math.abs(net))} <small>MW</small>
            </b>
          </span>
        </div>
      </div>
    </div>
  );
}
