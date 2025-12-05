from datetime import datetime

from pydantic import BaseModel, Field

NUM_INTERVALS = 11
INTERVAL_MINUTES = 5
INTERVAL_HOURS = INTERVAL_MINUTES / 60


class BatteryConfig(BaseModel):
    """Battery physical specifications and operational constraints."""

    capacity_mwh: float = Field(default=100.0, description="Total energy storage capacity in MWh")
    max_power_mw: float = Field(
        default=100.0, description="Maximum charging/discharging power in MW"
    )
    roundtrip_efficiency: float = Field(
        default=0.85,
        description="Round-trip efficiency (0-1), accounting for energy losses in both charging and discharging",
    )
    soc_min_pct: float = Field(
        default=0.05,
        description="Minimum state of charge as percentage (0-1) to prevent battery degradation",
    )
    soc_max_pct: float = Field(
        default=0.95,
        description="Maximum state of charge as percentage (0-1) to prevent battery degradation",
    )
    # hurdle_cost_per_mwh: float = Field(
    #     default=0.0,
    #     description="Penalty per MWh cycled to account for battery cycling costs.",
    # )

    @property
    def soc_min_mwh(self) -> float:
        """Minimum state of charge in MWh."""
        return self.capacity_mwh * self.soc_min_pct

    @property
    def soc_max_mwh(self) -> float:
        """Maximum state of charge in MWh."""
        return self.capacity_mwh * self.soc_max_pct


class BacktestConfig(BaseModel):
    """Configuration for backtest execution."""

    start_time: datetime | None = Field(
        default=None,
        description="Start time for the backtest period. If None, uses the first row in the data",
    )
    end_time: datetime | None = Field(
        default=None,
        description="End time for the backtest period. If None, uses last row in the data",
    )
    initial_soc_pct: float = Field(
        default=0.5,
        description="Initial state of charge as percentage (0-1) at the start of backtest",
    )
    horizon_intervals: int = Field(
        default=NUM_INTERVALS,
        description="Number of future intervals to forecast/optimize over when making decisions. With 5-min intervals, 11 = 55 minutes ahead.",
    )


class BatteryOptimizationConfig(BaseModel):
    """Configuration for optimization-based strategies."""

    horizon_intervals: int = Field(
        default=NUM_INTERVALS,
        description="Number of future time intervals to optimize over. Longer horizons capture more arbitrage opportunities but increase computation time",
    )
    min_buy_price: float | None = Field(
        default=25.0,
        description="Optional minimum price threshold ($/MWh) below which to consider buying/charging. In combination with max_sell_price, this can be used to create an implicit hurdle cost for cycling.",
    )
    max_sell_price: float | None = Field(
        default=50.0,
        description="Optional maximum price threshold ($/MWh) above which to consider selling/discharging.  In combination with min_buy_price, this can be used to create an implicit hurdle cost for cycling",
    )


class ConfigurableNonOptimizationStrategyConfig(BaseModel):
    """Configuration for simple price-taker threshold strategy."""

    high_discharge_price_threshold: float = Field(
        default=100.0,
        description="Forecasted price threshold ($/MWh) above which to discharge at maximum power. When forecast > this threshold, we want to sell and discharge aggressively",
    )
    discharge_bid_price: float = Field(
        default=-249.0,
        description="Bid price ($/MWh) to offer when discharging. Set low to ensure clearance.",
    )
    low_charge_price_threshold: float = Field(
        default=10.0,
        description="Forecasted price threshold ($/MWh) below which to charge at maximum power. When forecast < this threshold, we want to buy and charge aggressively",
    )
    charge_bid_price: float = Field(
        default=5000.0,
        description="Bid price ($/MWh) to offer when charging. Set high to ensure clearance.",
    )
