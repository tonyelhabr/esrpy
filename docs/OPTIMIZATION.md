# Optimization & Trading Strategies

This document describes the trading strategies implemented in `strategies.py`.

## `ConfigurableOptimizationStrategy`

### Objective

Maximize energy arbitrage revenue over 11 five-minute intervals (55-minute horizon).

In symbols, maximize `Σ(t=0 to 10) [power[t] × price[t] × Δt]`
where `Δt = 5 minutes` and `price[t]` are given forecasted prices.

### Decision Variables

- `power[t]`: Net power (MW) at each interval `t = 0, 1, ..., 10`
- `soc[t]`: State of charge (MWh) at each time point `t = 0, 1, ..., 11`

### Constraints

1. SoC initialization: `soc[0] = initial_soc`
2. SoC transition: `soc[t+1] = soc[t] - power[t] × Δt / η`  (where `η` is efficiency)
3. SoC limits: `soc_min ≤ soc[t] ≤ soc_max` for all `t`
4. Power limits: `-p_max ≤ power[t] ≤ p_max` for all `t`

### Post-Processing

After optimization, the first interval decision `power[0]` can be set to 0 under certain conditions:

- If `power[0] > 0` (discharge) and `price[0] < max_sell_price` (e.g. $50)
- If `power[0] < 0` (charge) and `price[0] > min_buy_price` (e.g. $25)

This is primarily for risk mitigation, but also serves as a "bandaid" for not modeling ["hurdle" / cycling costs](https://www.tyba.ai/resources/case-studies/ercot-operating-strategy-asset-cycling/) explicitly.

## Strategy Comparison

It's important to contextualize one's strategy. One can do this with:

1. A "simple" baseline—`ConfigurableNonOptimizationStrategy` that does not use optimization—to provide a lower bound on expected profit
2. A strategy that is exactly like `ConfigurableOptimizationStrategy`, but has perfect information. This provides an upper bound on expected profit. (This is specified as `perfect_foresight` in `main.py`.)

### `ConfigurableNonOptimizationStrategy`

Make trading decisions based solely on the current 5-minute price forecast using simple thresholds.

#### Decision Rules

1. If `price[0] > high_discharge_price_threshold` (default: $100), submit "price-taker" sell offer at `discharge_bid_price` (default: -$249) to discharge at maximum available power.
2. If `price[0] < low_charge_price_threshold` (default: $10), submit "price-taker" buy bid at `charge_bid_price` (default: $5,000) to charge at maximum available power
3. Otherwise, do nothing

