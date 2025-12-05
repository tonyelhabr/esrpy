import logging
from datetime import datetime, timedelta

import numpy as np
import polars as pl

from .config import NUM_INTERVALS

logger = logging.getLogger(__name__)


class PointInTimeData:
    """
    Handles point-in-time data retrieval.
    """

    def __init__(self, forecast_df: pl.DataFrame, actual_df: pl.DataFrame):
        """
        Initialize with forecast and actual price data.
        """
        self.forecast_df = forecast_df.sort(["as_of_cpt", "interval_end_cpt"])
        self.actual_df = actual_df.sort("interval_end_cpt")

    def get_forecasted_prices(
        self,
        for_timestamp: datetime,
        as_of: datetime,
        horizon_intervals: int = NUM_INTERVALS,
    ) -> np.ndarray:
        """
        Get price forecast with point-in-time correctness.
        """

        target_timestamps = np.array(
            [for_timestamp + timedelta(minutes=5 * i) for i in range(horizon_intervals)]
        )

        forecasted_prices = np.full(horizon_intervals, np.nan)

        for i, target_ts in enumerate(target_timestamps):
            forecast_row = (
                self.forecast_df.filter(
                    (pl.col("as_of_cpt") <= as_of)
                    & (pl.col("interval_end_cpt") == target_ts)
                )
                .sort("as_of_cpt", descending=True)
                .head(1)
            )

            if len(forecast_row) > 0:
                forecasted_prices[i] = forecast_row["lmp"][0]
            else:
                break

        valid_forecast_prices = forecasted_prices[~np.isnan(forecasted_prices)]

        if len(valid_forecast_prices) == 0:
            logger.warning(f"No forecasts available for {for_timestamp} as of {as_of}")

        return valid_forecast_prices

    def get_actual_price(self, timestamp: datetime) -> float | None:
        """Get actual cleared price for a timestamp."""
        result = self.actual_df.filter(pl.col("interval_end_cpt") == timestamp).select(
            "lmp"
        )

        if len(result) == 0:
            return None

        return float(result["lmp"][0])

    def get_perfect_foresight_actual_prices(
        self,
        from_timestamp: datetime,
        horizon_intervals: int = NUM_INTERVALS,
    ) -> np.ndarray:
        """
        Get future actual prices (for perfect foresight backtesting only).
        """
        target_timestamps = np.array(
            [from_timestamp + timedelta(minutes=5 * i) for i in range(horizon_intervals)]
        )

        actual_prices = np.full(horizon_intervals, np.nan)

        for i, target_ts in enumerate(target_timestamps):
            result = self.actual_df.filter(pl.col("interval_end_cpt") == target_ts).select(
                "lmp"
            )

            if len(result) > 0:
                actual_prices[i] = result["lmp"][0]
            else:
                break

        valid_actual_prices = actual_prices[~np.isnan(actual_prices)]

        return valid_actual_prices
