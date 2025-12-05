from pathlib import Path

import polars as pl
import pytest

from esrpy.data_loader import (
    _load_actual_lmps,
    _load_indicative_lmps,
    load_lmps,
)
from esrpy.schemas import ActualLmpSchema, IndicativeLmpSchema


class TestLoadLmps:
    """Test the load_lmps function and helpers."""

    def test_load_actual_lmps(self):
        """Test loading actual LMPs from CSV."""
        csv_path = Path(__file__).parent / "test_actual_lmps.csv"
        actual_lmps = _load_actual_lmps(csv_path)

        assert isinstance(actual_lmps, pl.DataFrame)
        assert set(actual_lmps.columns) == {"interval_end_cpt", "lmp"}
        assert actual_lmps["interval_end_cpt"].dtype == pl.Datetime(time_zone="America/Chicago")
        assert len(actual_lmps) == 12

        # Check first value
        assert actual_lmps["lmp"][0] == pytest.approx(22.67, abs=0.01)

        # Validate against schema
        ActualLmpSchema.validate(actual_lmps)

    def test_load_indicative_lmps(self):
        """Test loading indicative LMPs from CSV."""
        csv_path = Path(__file__).parent / "test_indicative_lmps.csv"
        indicative_lmps = _load_indicative_lmps(csv_path)

        assert isinstance(indicative_lmps, pl.DataFrame)
        assert set(indicative_lmps.columns) == {
            "as_of_cpt",
            "interval_end_cpt",
            "horizon_5min_idx",
            "lmp",
        }
        # Check column order
        assert list(indicative_lmps.columns) == [
            "as_of_cpt",
            "interval_end_cpt",
            "horizon_5min_idx",
            "lmp",
        ]
        assert indicative_lmps["interval_end_cpt"].dtype == pl.Datetime(time_zone="America/Chicago")
        assert indicative_lmps["as_of_cpt"].dtype == pl.Datetime(time_zone="America/Chicago")
        assert indicative_lmps["horizon_5min_idx"].dtype == pl.Int32

        # Validate against schema
        IndicativeLmpSchema.validate(indicative_lmps)

    def test_load_both_files(self):
        """Test loading both actual and indicative LMPs."""
        actual_csv = Path(__file__).parent / "test_actual_lmps.csv"
        indicative_csv = Path(__file__).parent / "test_indicative_lmps.csv"

        indicative_lmps, actual_lmps = load_lmps(actual_csv, indicative_csv)

        assert isinstance(indicative_lmps, pl.DataFrame)
        assert isinstance(actual_lmps, pl.DataFrame)

        # Both should pass schema validation
        ActualLmpSchema.validate(actual_lmps)
        IndicativeLmpSchema.validate(indicative_lmps)

    def test_horizon_loaded_correctly(self):
        """Test that horizon_5min_idx is loaded correctly from CSV."""
        csv_path = Path(__file__).parent / "test_indicative_lmps.csv"
        indicative_lmps = _load_indicative_lmps(csv_path)

        # For as_of=00:00, interval_end=00:05, horizon should be 1
        horizon_1 = indicative_lmps.filter(
            (pl.col("horizon_5min_idx") == 1)
        )
        assert len(horizon_1) > 0

        # For as_of=00:00, interval_end=00:55, horizon should be 11
        horizon_11 = indicative_lmps.filter(
            (pl.col("horizon_5min_idx") == 11)
        )
        assert len(horizon_11) > 0

    def test_timezone_preserved(self):
        """Test that timestamps are kept in America/Chicago timezone."""
        csv_path = Path(__file__).parent / "test_actual_lmps.csv"
        actual_lmps = _load_actual_lmps(csv_path)

        # Input is 2025-10-01 00:05:00 CDT
        # Output should stay 2025-10-01 00:05:00 CDT
        first_ts = actual_lmps["interval_end_cpt"][0]
        assert first_ts.hour == 0  # Stays at 00:05 CDT

    def test_horizon_matches_timestamps(self):
        """Test that horizon_5min_idx matches the timestamp difference."""
        csv_path = Path(__file__).parent / "test_indicative_lmps.csv"
        indicative_lmps = _load_indicative_lmps(csv_path)

        # Get a horizon=1 forecast
        horizon_1 = indicative_lmps.filter(pl.col("horizon_5min_idx") == 1).head(1)

        if len(horizon_1) > 0:
            interval_end = horizon_1["interval_end_cpt"][0]
            as_of_cpt = horizon_1["as_of_cpt"][0]

            # For horizon=1, interval_end should be 5 min after as_of_cpt
            expected_diff_seconds = 5 * 60
            actual_diff_seconds = (interval_end - as_of_cpt).total_seconds()
            assert actual_diff_seconds == expected_diff_seconds
