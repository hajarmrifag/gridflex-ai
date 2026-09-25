"""Bounded, strict request contracts for the public simulation API."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Profile(str, Enum):
    morocco = "morocco"
    germany = "germany"
    synthetic = "synthetic"


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    profile: Profile = Profile.morocco
    days: Literal[7, 14, 30, 60] = 30
    penetration_pct: float = Field(default=90, ge=0, le=150)
    flexibility_pct: float = Field(default=10, ge=0, le=30)
    power_pct: float = Field(default=15, ge=1, le=50)
    duration_h: float = Field(default=4, ge=0, le=12)
    efficiency_pct: float = Field(default=90, ge=50, le=100)
    peak_quantile: float = Field(default=0.72, ge=0.5, le=0.95)


class OptimizeRequest(ScenarioRequest):
    allow_grid_charging: bool = False
    restore_soc: bool = False


class StressRequest(ScenarioRequest):
    demand_shock_pct: float = Field(default=25, ge=0, le=100)
    renewable_drop_pct: float = Field(default=40, ge=0, le=100)
