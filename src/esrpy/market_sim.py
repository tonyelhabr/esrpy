from datetime import timedelta

import numpy as np

from .config import INTERVAL_HOURS, INTERVAL_MINUTES, BatteryConfig
from .schemas import BatteryState, IntervalPnL, MarketOffer, MarketOutcome


def simulate_market_clearing(offer: MarketOffer, clearing_price: float) -> MarketOutcome:
    """
    Simulate if our offer would be accepted in market clearing.
    """
    if offer.power_mw > 0:
        awarded = offer.price_offer <= clearing_price
    elif offer.power_mw < 0:
        awarded = offer.price_offer >= clearing_price
    else:
        awarded = False

    executed_power = offer.power_mw if awarded else 0.0

    return MarketOutcome(
        timestamp=offer.timestamp,
        clearing_price=clearing_price,
        awarded=awarded,
        executed_power_mw=executed_power,
    )


def update_battery_state(
    state: BatteryState,
    executed_power_mw: float,
    config: BatteryConfig,
) -> BatteryState:
    """
    Update battery state based on executed power.
    """

    if executed_power_mw > 0:
        soc_change = -executed_power_mw * INTERVAL_HOURS / config.roundtrip_efficiency**0.5
    elif executed_power_mw < 0:
        soc_change = -executed_power_mw * INTERVAL_HOURS * config.roundtrip_efficiency**0.5
    else:
        soc_change = 0.0

    new_soc = state.soc_mwh + soc_change

    new_soc = float(np.clip(new_soc, config.soc_min_mwh, config.soc_max_mwh))

    return BatteryState(
        timestamp=state.timestamp + timedelta(minutes=INTERVAL_MINUTES),
        soc_mwh=new_soc,
        last_power_mw=executed_power_mw,
    )


def calculate_interval_pnl(
    outcome: MarketOutcome,
    # config: BatteryConfig,
) -> IntervalPnL:
    """
    Calculate P&L for one interval.
    """

    energy_revenue_usd = outcome.executed_power_mw * outcome.clearing_price * INTERVAL_HOURS

    # charge_mwh = abs(min(outcome.executed_power_mw, 0)) * INTERVAL_HOURS
    # discharge_mwh = max(outcome.executed_power_mw, 0) * INTERVAL_HOURS
    # hurdle_cost_usd = (charge_mwh + discharge_mwh) * config.hurdle_cost_per_mwh
    # net_pnl_usd = energy_revenue_usd - hurdle_cost_usd

    return IntervalPnL(
        energy_revenue_usd=energy_revenue_usd,
        # hurdle_cost_usd=hurdle_cost_usd,
        net_pnl_usd=energy_revenue_usd,
    )
