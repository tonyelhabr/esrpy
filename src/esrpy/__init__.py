"""esrpy - Battery optimization backtest framework for energy storage resources."""

from .backtest import analyze_backtest_results, run_backtest
from .config import BacktestConfig, BatteryConfig, BatteryOptimizationConfig
from .data_loader import load_lmps
from .plots import plot_single_backtest
from .point_in_time_data import PointInTimeData
from .strategies import (
    ConfigurableNonOptimizationStrategy,
    ConfigurableOptimizationStrategy,
    TradingStrategy,
)

__all__ = [
    "analyze_backtest_results",
    "run_backtest",
    "BacktestConfig",
    "BatteryConfig",
    "BatteryOptimizationConfig",
    "load_lmps",
    "plot_single_backtest",
    "PointInTimeData",
    "ConfigurableNonOptimizationStrategy",
    "ConfigurableOptimizationStrategy",
    "TradingStrategy",
]

