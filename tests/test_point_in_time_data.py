from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

from esrpy.point_in_time_data import PointInTimeData

TZ = ZoneInfo("America/Chicago")


class TestGetForecastedPrices:
    """Test PointInTimeData.get_forecasted_prices method."""

    def test_get_forecasted_prices_basic(self, sample_forecast_data, sample_actual_data):
        """Test basic forecast retrieval."""
        pit_data = PointInTimeData(sample_forecast_data, sample_actual_data)

        base_time = datetime(2025, 10, 1, 0, 5, 0, tzinfo=TZ)
        as_of = base_time - timedelta(minutes=5)
        forecasted_prices = pit_data.get_forecasted_prices(base_time, as_of, horizon_intervals=11)

        assert isinstance(forecasted_prices, np.ndarray)
        assert len(forecasted_prices) > 0
        assert all(~np.isnan(forecasted_prices))

    def test_get_forecasted_prices_returns_most_recent(self):
        """Test that get_forecasted_prices returns the most recent forecast."""
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TZ)
        target_time = base_time + timedelta(minutes=5)

        forecast_data = pl.DataFrame(
            {
                "interval_end_cpt": [target_time] * 3,
                "as_of_cpt": [
                    base_time - timedelta(minutes=15),
                    base_time - timedelta(minutes=10),
                    base_time - timedelta(minutes=5),
                ],
                "horizon_5min_idx": [1, 1, 1],
                "lmp": [20.0, 25.0, 30.0],
            }
        ).with_columns(pl.col("horizon_5min_idx").cast(pl.Int32))

        actual_data = pl.DataFrame(
            {
                "interval_end_cpt": [target_time],
                "lmp": [28.0],
            }
        )

        pit_data = PointInTimeData(forecast_data, actual_data)
        forecasted_prices = pit_data.get_forecasted_prices(
            target_time, base_time, horizon_intervals=1
        )

        assert len(forecasted_prices) == 1
        assert forecasted_prices[0] == 30.0

    def test_get_forecasted_prices_point_in_time_correctness(self):
        """Test that get_forecasted_prices respects point-in-time constraints."""
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TZ)
        target_time = base_time + timedelta(minutes=5)

        forecast_data = pl.DataFrame(
            {
                "interval_end_cpt": [target_time],
                "as_of_cpt": [base_time + timedelta(minutes=5)],
                "horizon_5min_idx": [1],
                "lmp": [30.0],
            }
        ).with_columns(pl.col("horizon_5min_idx").cast(pl.Int32))

        actual_data = pl.DataFrame(
            {
                "interval_end_cpt": [target_time],
                "lmp": [28.0],
            }
        )

        pit_data = PointInTimeData(forecast_data, actual_data)
        forecasted_prices = pit_data.get_forecasted_prices(
            target_time, base_time, horizon_intervals=1
        )

        assert len(forecasted_prices) == 0

    def test_get_forecasted_prices_no_data_available(
        self, sample_forecast_data, sample_actual_data
    ):
        """Test forecast retrieval when no data is available."""
        pit_data = PointInTimeData(sample_forecast_data, sample_actual_data)

        early_time = datetime(202, 1, 1, 0, 0, 0, tzinfo=TZ)
        forecasted_prices = pit_data.get_forecasted_prices(
            early_time, early_time, horizon_intervals=11
        )

        assert isinstance(forecasted_prices, np.ndarray)
        assert len(forecasted_prices) == 0

    def test_get_forecasted_prices_partial_horizon(self):
        """Test that forecast returns partial results if full horizon unavailable."""
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TZ)

        forecast_data = pl.DataFrame(
            {
                "interval_end_cpt": [base_time + timedelta(minutes=5 * i) for i in range(3)],
                "as_of_cpt": [base_time - timedelta(minutes=5)] * 3,
                "horizon_5min_idx": [1, 2, 3],
                "lmp": [25.0, 26.0, 27.0],
            }
        ).with_columns(pl.col("horizon_5min_idx").cast(pl.Int32))

        actual_data = pl.DataFrame(
            {
                "interval_end_cpt": [base_time],
                "lmp": [25.0],
            }
        )

        pit_data = PointInTimeData(forecast_data, actual_data)
        forecasted_prices = pit_data.get_forecasted_prices(
            base_time, base_time - timedelta(minutes=5), horizon_intervals=11
        )

        assert len(forecasted_prices) == 3


class TestGetPerfectForesightActualPrices:
    """Test PointInTimeData.get_perfect_foresight_actual_prices method."""

    def test_get_perfect_foresight_actual_prices_basic(
        self, sample_forecast_data, sample_actual_data
    ):
        """Test basic perfect foresight actuals retrieval."""
        pit_data = PointInTimeData(sample_forecast_data, sample_actual_data)

        base_time = datetime(2025, 10, 1, 0, 5, 0, tzinfo=TZ)
        actual_prices = pit_data.get_perfect_foresight_actual_prices(
            base_time, horizon_intervals=10
        )

        assert isinstance(actual_prices, np.ndarray)
        assert len(actual_prices) > 0
        assert all(~np.isnan(actual_prices))

    def test_get_perfect_foresight_actual_prices_correct_timestamps(self):
        """Test that perfect foresight returns correct timestamps."""
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TZ)

        actual_data = pl.DataFrame(
            {
                "interval_end_cpt": [base_time + timedelta(minutes=5 * i) for i in range(3)],
                "lmp": [25.0, 26.0, 27.0],
            }
        )

        forecast_data = pl.DataFrame(
            {
                "interval_end_cpt": [],
                "as_of_cpt": [],
                "horizon_5min_idx": [],
                "lmp": [],
            }
        ).cast(
            {
                "interval_end_cpt": pl.Datetime(time_zone="America/Chicago"),
                "as_of_cpt": pl.Datetime(time_zone="America/Chicago"),
                "horizon_5min_idx": pl.Int32,
                "lmp": pl.Float64,
            }
        )

        pit_data = PointInTimeData(forecast_data, actual_data)
        actual_prices = pit_data.get_perfect_foresight_actual_prices(base_time, horizon_intervals=3)

        assert len(actual_prices) == 3
        np.testing.assert_array_equal(actual_prices, [25.0, 26.0, 27.0])

    def test_get_perfect_foresight_actual_prices_partial_data(self):
        """Test perfect foresight with partial data available."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=TZ)

        actual_data = pl.DataFrame(
            {
                "interval_end_cpt": [base_time + timedelta(minutes=5 * i) for i in range(3)],
                "lmp": [25.0, 26.0, 27.0],
            }
        )

        forecast_data = pl.DataFrame(
            {
                "interval_end_cpt": [],
                "as_of_cpt": [],
                "horizon_5min_idx": [],
                "lmp": [],
            }
        ).cast(
            {
                "interval_end_cpt": pl.Datetime(time_zone="America/Chicago"),
                "as_of_cpt": pl.Datetime(time_zone="America/Chicago"),
                "horizon_5min_idx": pl.Int32,
                "lmp": pl.Float64,
            }
        )

        pit_data = PointInTimeData(forecast_data, actual_data)
        actual_prices = pit_data.get_perfect_foresight_actual_prices(
            base_time, horizon_intervals=11
        )

        assert len(actual_prices) == 3
