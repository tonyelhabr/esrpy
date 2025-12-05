from datetime import timedelta

import polars as pl

from .config import (
    INTERVAL_HOURS,
    INTERVAL_MINUTES,
    BacktestConfig,
    BatteryConfig,
)
from .market_sim import calculate_interval_pnl, simulate_market_clearing, update_battery_state
from .point_in_time_data import PointInTimeData
from .schemas import BacktestResultSchema, BacktestSummary, BatteryState
from .strategies import TradingStrategy


def run_backtest(
    pit_data: PointInTimeData,
    strategy: TradingStrategy,
    battery_config: BatteryConfig,
    backtest_config: BacktestConfig,
    use_perfect_foresight: bool = False,
) -> BacktestResultSchema:
    """
    Run backtest stepping through time.
    """

    if backtest_config.start_time is None:
        backtest_config.start_time = pit_data.actual_df["interval_end_cpt"].min()
    if backtest_config.end_time is None:
        backtest_config.end_time = pit_data.actual_df["interval_end_cpt"].max()

    start_time = backtest_config.start_time
    end_time = backtest_config.end_time

    state = BatteryState(
        timestamp=start_time,
        soc_mwh=battery_config.capacity_mwh * backtest_config.initial_soc_pct,
    )

    results = []
    current_time = start_time

    interval_count = 0

    while current_time < end_time:
        if use_perfect_foresight:
            forecasted_prices = pit_data.get_perfect_foresight_actual_prices(
                from_timestamp=current_time,
                horizon_intervals=backtest_config.horizon_intervals,
            )
        else:
            forecasted_prices = pit_data.get_forecasted_prices(
                for_timestamp=current_time,
                as_of=current_time,
                horizon_intervals=backtest_config.horizon_intervals,
            )

        if len(forecasted_prices) == 0:
            current_time += timedelta(minutes=INTERVAL_MINUTES)
            continue

        offer = strategy.make_offer(
            state=state,
            config=battery_config,
            forecasted_prices=forecasted_prices,
        )

        actual_price = pit_data.get_actual_price(current_time)
        if actual_price is None:
            current_time += timedelta(minutes=INTERVAL_MINUTES)
            continue

        outcome = simulate_market_clearing(offer, actual_price)

        pnl = calculate_interval_pnl(
            outcome,
            # battery_config,
        )

        soc_start = state.soc_mwh
        state = update_battery_state(
            state,
            outcome.executed_power_mw,
            battery_config,
        )

        discharge_mwh = max(outcome.executed_power_mw, 0) * INTERVAL_HOURS
        charge_mwh = abs(min(outcome.executed_power_mw, 0)) * INTERVAL_HOURS

        results.append(
            {
                "interval_end_cpt": current_time,
                "price_forecast": float(forecasted_prices[0]),
                "price_actual": actual_price,
                "offer_power_mw": offer.power_mw,
                "offer_price": offer.price_offer,
                "awarded": outcome.awarded,
                "executed_power_mw": outcome.executed_power_mw,
                "energy_revenue_usd": pnl.energy_revenue_usd,
                # "hurdle_cost_usd": pnl.hurdle_cost_usd,
                "net_pnl_usd": pnl.net_pnl_usd,
                "soc_start_mwh": soc_start,
                "soc_end_mwh": state.soc_mwh,
                "discharge_mwh": discharge_mwh,
                "charge_mwh": charge_mwh,
            }
        )

        interval_count += 1
        current_time += timedelta(minutes=INTERVAL_MINUTES)

    results_df = pl.DataFrame(results)
    results_df = results_df.with_columns(pl.col("net_pnl_usd").cum_sum().alias("cumu_net_pnl_usd"))
    results_df = BacktestResultSchema.validate(results_df)

    return results_df


def analyze_backtest_results(results_df: pl.DataFrame, config: BatteryConfig) -> BacktestSummary:
    """
    Generate summary statistics from backtest results.
    """

    total_pnl = float(results_df["net_pnl_usd"].sum())
    total_revenue = float(results_df["energy_revenue_usd"].sum())
    # total_hurdle_cost_usd = float(results_df["hurdle_cost_usd"].sum())

    discharge_df = results_df.filter(pl.col("executed_power_mw") > 0)
    charge_df = results_df.filter(pl.col("executed_power_mw") < 0)

    discharge_revenue = (
        float(discharge_df["energy_revenue_usd"].sum()) if len(discharge_df) > 0 else 0.0
    )
    charge_cost = float(charge_df["energy_revenue_usd"].sum()) if len(charge_df) > 0 else 0.0

    total_charged_mwh = (
        abs(float(charge_df["executed_power_mw"].sum()) * INTERVAL_HOURS)
        if len(charge_df) > 0
        else 0.0
    )
    total_discharged_mwh = (
        float(discharge_df["executed_power_mw"].sum()) * INTERVAL_HOURS
        if len(discharge_df) > 0
        else 0.0
    )
    total_cycles = (total_charged_mwh + total_discharged_mwh) / config.capacity_mwh

    return BacktestSummary(
        total_pnl=round(total_pnl, 2),
        total_revenue=round(total_revenue, 2),
        discharge_revenue=round(discharge_revenue, 2),
        charge_cost=round(charge_cost, 2),
        total_cycles=round(total_cycles, 2),
        num_intervals=len(results_df),
        num_awarded=int(results_df["awarded"].sum()),
        award_rate=round(float(results_df["awarded"].mean()), 2),
        avg_pnl_per_interval=round(total_pnl / len(results_df), 2),
        total_charged_mwh=round(total_charged_mwh, 2),
        total_discharged_mwh=round(total_discharged_mwh, 2),
    )
