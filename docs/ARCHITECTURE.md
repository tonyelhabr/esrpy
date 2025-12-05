# esrpy

Energy Storage Resources (ESR) is the formal name for batteries operating in ERCOT. This Python package allows one to configure a RT strategy for operating the battery, pre-RTC+B.

## Overview

This document describes the architecture, data flow, and trade-offs made in the design of a backtest framework for a hypothetical battery in ERCOT looking to maximize real-time energy profit. The codebase is designed for flexibility, testability, and easy experimentation. The actual optimization formulation--see `ConfigurableOptimizationStrategy`--itself may not be perfect.

## System Architecture

### Project Structure

```
ee/
├── src/esrpy/                   # Main package
│   ├── __init__.py              # Public API exports
│   ├── backtest.py              # Backtest orchestration
│   ├── config.py                # Pydantic configuration classes
│   ├── data_loader.py           # CSV loading and validation
│   ├── market_sim.py            # Market simulation and battery state
│   ├── point_in_time_data.py    # Point-in-time data retrieval
│   ├── plots.py                 # Visualization utilities
│   ├── schemas.py               # Pandera schemas for data validation
│   └── strategies.py            # Trading strategy implementations
│
├── notebooks/
│   ├── data_retrieval.ipynb     # Fetch input data from ERCOT
│   └── generate_test_fixtures.ipynb
│
├── tests/
└── pyproject.toml
```

### Data Flow

```
load_lmps() [data_loader.py]
  ↓
PointInTimeData [point_in_time_data.py]
  ↓
run_backtest() [backtest.py]
  ├─ For each timestamp:
  │   ├─ get_forecasted_prices()
  │   ├─ TradingStrategy.make_offer() → MarketOffer
  │   ├─ simulate_market_clearing() → MarketOutcome
  │   ├─ get_actual_price()
  │   ├─ calculate_interval_pnl() → IntervalPnL
  │   └─ update_battery_state() → BatteryState
  ↓
Results DataFrame → BacktestResultSchema
  ↓
analyze_backtest_results() → BacktestSummary
```

## Key Design Decisions

### Trading Strategies

See [OPTIMIZATION.md](OPTIMIZATION.md) for details on the optimization formulation and strategy comparisons.

### Point-in-time correctness (in `point_in_time_data.py`)

The `PointInTimeData` class ensures that the latest forecasts available at decision time are used for backtesting. No matter how sound your optimization formulation is, if the data underpinning it has look-ahead bias, then you can't trust the results.

## Tradeoffs & Improvements

### Current Tradeoffs

1. Deals with a simplified problem where timestamps are pre-rounded to 5-minute intervals, which overlooks the fact that there are some intervals with multiple SCED runs.
2. Does not consider making offer curves, and instead chose to make singular P-Q pair offers.
3. Does not consider a more economic bidding strategy, such as bidding x% higher than my forecasted price to ensure higher probability of clearance.

### Potential Improvements

#### Strategies

1. Account for "hurdle" / cycling cost.
2. Account for forecast error, perhaps with some simple corrections tracking last N errors relative to the real-time.
3. Modify the simple strategy to use the latest actual price instead of a forecasted price so as to make it even more fail-safe.
4. Consider different / better risk mitigation measures, e.g. flexible price thresholds.
5. Consider adding location-agnostic performance metrics, such as [TB1 capture rate](https://www.gridmatic.com/impact-of-location-and-optimization-on-maximizing-bess-revenue/).
6. Consider how to expand the problem for AS products and for DA energy.

#### Logistics

1. Enable code to run backtests in parallel.
2. Consider how to mitigate missing forecasts and actuals data.
3. Resolve non-determinism. (Re-runs with the same data produce slightly different results.)
