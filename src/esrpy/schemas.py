from datetime import datetime

import pandera.polars as pa
import polars as pl
from pydantic import BaseModel, Field

from .config import NUM_INTERVALS


class IndicativeLmpSchema(pa.DataFrameModel):
    """Schema for indicative (forecasted) LMP data."""

    as_of_cpt: pl.Datetime(time_zone="America/Chicago") = pa.Field()
    interval_end_cpt: pl.Datetime(time_zone="America/Chicago") = pa.Field(coerce=False)
    horizon_5min_idx: pl.Int32 = pa.Field(ge=0, le=NUM_INTERVALS)
    lmp: pl.Float64 = pa.Field(nullable=False)

    class Config:
        strict = True


class ActualLmpSchema(pa.DataFrameModel):
    """Schema for actual LMP data."""

    interval_end_cpt: pl.Datetime(time_zone="America/Chicago") = pa.Field(coerce=False)
    lmp: pl.Float64 = pa.Field(nullable=False)

    class Config:
        strict = True


class BacktestResultSchema(pa.DataFrameModel):
    """Schema for backtest results."""

    interval_end_cpt: pl.Datetime(time_zone="America/Chicago") = pa.Field(coerce=False)
    price_forecast: pl.Float64
    price_actual: pl.Float64
    offer_power_mw: pl.Float64
    offer_price: pl.Float64
    awarded: pl.Boolean
    executed_power_mw: pl.Float64
    energy_revenue_usd: pl.Float64
    # hurdle_cost_usd: pl.Float64
    net_pnl_usd: pl.Float64
    soc_start_mwh: pl.Float64
    soc_end_mwh: pl.Float64
    discharge_mwh: pl.Float64
    charge_mwh: pl.Float64
    cumu_net_pnl_usd: pl.Float64

    class Config:
        strict = True


class BatteryState(BaseModel):
    """Current battery state at a point in time."""

    timestamp: datetime
    soc_mwh: float
    last_power_mw: float = Field(
        default=0.0,
        description="Power output in the previous interval (MW). Positive = discharging, negative = charging",
    )


class MarketOffer(BaseModel):
    """Bid/offer to the market."""

    timestamp: datetime
    power_mw: float = Field(
        description="Power to bid (MW). Positive = sell (discharge), negative = buy (charge)"
    )
    price_offer: float


class MarketOutcome(BaseModel):
    """Result of market clearing for our offer."""

    timestamp: datetime
    clearing_price: float
    awarded: bool
    executed_power_mw: float = Field(
        description="Actual power delivered (MW). Positive = discharged, negative = charged"
    )


class IntervalPnL(BaseModel):
    """P&L calculation for a single market interval."""

    energy_revenue_usd: float
    # hurdle_cost_usd: float = Field(description="Hurdle cost in USD")
    net_pnl_usd: float

    class ConfigDict:
        frozen = True


class BacktestSummary(BaseModel):
    """Summary statistics from backtest results."""

    total_pnl: float
    total_revenue: float
    discharge_revenue: float
    charge_cost: float
    total_cycles: float
    num_intervals: int
    num_awarded: int
    award_rate: float
    avg_pnl_per_interval: float
    total_charged_mwh: float
    total_discharged_mwh: float

    class ConfigDict:
        frozen = True
