from pathlib import Path

import polars as pl
import pytest


@pytest.fixture
def sample_forecast_data():
    """
    Load sample indicative LMP data from CSV for testing.

    Uses the raw format from data_retrieval.ipynb with columns:
    as_of_cpt, interval_start_cpt, interval_end_cpt, horizon_5min_idx, lmp
    """
    csv_path = Path(__file__).parent / "test_indicative_lmps.csv"

    df = pl.read_csv(csv_path).with_columns(
        [
            pl.col("interval_end_cpt").str.to_datetime().dt.replace_time_zone("America/Chicago"),
            pl.col("as_of_cpt").str.to_datetime().dt.replace_time_zone("America/Chicago"),
            pl.col("horizon_5min_idx").cast(pl.Int32),
        ]
    )

    return df


@pytest.fixture
def sample_actual_data():
    """
    Load sample actual LMP data from CSV for testing.

    Uses the raw format from data_retrieval.ipynb with columns:
    interval_start_cpt, interval_end_cpt, lmp
    """
    csv_path = Path(__file__).parent / "test_actual_lmps.csv"

    df = pl.read_csv(csv_path).with_columns(
        pl.col("interval_end_cpt").str.to_datetime().dt.replace_time_zone("America/Chicago")
    )

    return df
