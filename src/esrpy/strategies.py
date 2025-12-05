import logging

import cvxpy as cp
import numpy as np

from .config import (
    INTERVAL_HOURS,
    BatteryConfig,
    BatteryOptimizationConfig,
    ConfigurableNonOptimizationStrategyConfig,
)
from .schemas import BatteryState, MarketOffer

logger = logging.getLogger(__name__)


class TradingStrategy:
    """Base class for trading strategies."""

    def make_offer(
        self,
        state: BatteryState,
        config: BatteryConfig,
        forecasted_prices: np.ndarray,
        **kwargs,
    ) -> MarketOffer:
        """Make trading decision."""
        raise NotImplementedError


class ConfigurableNonOptimizationStrategy(TradingStrategy):
    """Simple threshold-based strategy: discharge if price high, charge if low."""

    def __init__(self, strategy_config: ConfigurableNonOptimizationStrategyConfig | None = None):
        """Initialize simple strategy."""
        self.config = strategy_config or ConfigurableNonOptimizationStrategyConfig()

    def make_offer(
        self,
        state: BatteryState,
        config: BatteryConfig,
        forecasted_prices: np.ndarray,
        **kwargs,
    ) -> MarketOffer:
        """
        Make price-taker threshold-based trading decision.

        Strategy:
        - If forecasted price > high_discharge_price_threshold: discharge at max power, selling at low price
        - If forecasted price < low_charge_price_threshold: charge at max power, buying in at high price
        - Otherwise: offer 0 MW at the forecasted price

        Only tries to optimize over the next 5-minute interval.
        """
        price_forecast = float(forecasted_prices[0])

        # Manual-ish logic to enforce SoC and power limits.
        max_discharge_energy = state.soc_mwh - config.soc_min_mwh
        max_discharge_power = min(config.max_power_mw, max_discharge_energy / INTERVAL_HOURS)

        max_charge_energy = config.soc_max_mwh - state.soc_mwh
        max_charge_power = min(config.max_power_mw, max_charge_energy / INTERVAL_HOURS)

        if price_forecast > self.config.high_discharge_price_threshold:
            if max_discharge_power > 0:
                power = max_discharge_power
                offer_price = self.config.discharge_bid_price
            else:
                power = 0.0
                offer_price = price_forecast

        elif price_forecast < self.config.low_charge_price_threshold:
            if max_charge_power > 0:
                power = -max_charge_power
                offer_price = self.config.charge_bid_price
            else:
                power = 0.0
                offer_price = price_forecast

        else:
            power = 0.0
            offer_price = price_forecast

        return MarketOffer(
            timestamp=state.timestamp,
            power_mw=power,
            price_offer=offer_price,
        )


class ConfigurableOptimizationStrategy(TradingStrategy):
    """Optimization strategy using CVXPY."""

    def __init__(self, opt_config: BatteryOptimizationConfig | None = None):
        """Initialize optimization strategy."""
        self.config = opt_config or BatteryOptimizationConfig()
        logger.info(
            f"Initialized ConfigurableOptimizationStrategy with horizon={self.config.horizon_intervals}"
        )

    def make_offer(
        self,
        state: BatteryState,
        config: BatteryConfig,
        forecasted_prices: np.ndarray,
        **kwargs,
    ) -> MarketOffer:
        """
        Solve optimization problem with separate charge/discharge variables.
        """
        forecasted_prices = forecasted_prices[: self.config.horizon_intervals]
        num_intervals = len(forecasted_prices)
        price_forecast = float(forecasted_prices[0])

        power_discharge_mw = cp.Variable(num_intervals, name="power_discharge_mw", nonneg=True)
        power_charge_mw = cp.Variable(num_intervals, name="power_charge_mw", nonpos=True)
        soc_mwh = cp.Variable(num_intervals + 1, name="soc_mwh")

        net_power_mw = power_discharge_mw + power_charge_mw

        revenue = cp.sum(
            [net_power_mw[t] * forecasted_prices[t] * INTERVAL_HOURS for t in range(num_intervals)]
        )

        # TODO: Implement hurdle cost / shadow cost for cycling
        # This should represent the economic cost of battery degradation and cycling limits.
        # hurdle_cost = config.hurdle_cost_per_mwh * cp.sum(
        #     [(power_charge_mw[t] + power_discharge_mw[t]) * INTERVAL_HOURS for t in range(num_intervals)]
        # )

        objective = cp.Maximize(revenue)

        constraints = [
            soc_mwh[0] == state.soc_mwh,
        ]

        for t in range(num_intervals):
            constraints.extend(
                [
                    power_discharge_mw[t] <= config.max_power_mw,
                    power_charge_mw[t] >= -config.max_power_mw,
                    soc_mwh[t] >= config.soc_min_mwh,
                    soc_mwh[t] <= config.soc_max_mwh,
                ]
            )

            constraints.append(
                soc_mwh[t + 1]
                == soc_mwh[t]
                - INTERVAL_HOURS * power_discharge_mw[t] / config.roundtrip_efficiency**0.5
                - INTERVAL_HOURS * power_charge_mw[t] * config.roundtrip_efficiency**0.5
            )

        constraints.extend(
            [
                soc_mwh[num_intervals] >= config.soc_min_mwh,
                soc_mwh[num_intervals] <= config.soc_max_mwh,
            ]
        )

        problem = cp.Problem(objective, constraints)

        try:
            problem.solve(solver=cp.CLARABEL, verbose=False)

            if problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                optimal_power_discharge_mw = (
                    float(power_discharge_mw.value[0])
                    if power_discharge_mw.value is not None
                    else 0.0
                )
                optimal_power_charge_mw = (
                    float(power_charge_mw.value[0]) if power_charge_mw.value is not None else 0.0
                )
                optimal_power_mw = optimal_power_discharge_mw + optimal_power_charge_mw

                if self.config.min_buy_price is not None and optimal_power_mw < 0:
                    if price_forecast > self.config.min_buy_price:
                        optimal_power_mw = 0.0

                if self.config.max_sell_price is not None and optimal_power_mw > 0:
                    if price_forecast < self.config.max_sell_price:
                        optimal_power_mw = 0.0
            else:
                optimal_power_mw = 0.0

        except Exception as e:
            logger.error(f"Error solving optimization problem: {e}")
            optimal_power_mw = 0.0

        return MarketOffer(
            timestamp=state.timestamp,
            power_mw=optimal_power_mw,
            price_offer=price_forecast,
        )
