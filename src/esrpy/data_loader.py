import logging
from pathlib import Path

import polars as pl

from .config import NUM_INTERVALS
from .schemas import ActualLmpSchema, IndicativeLmpSchema

logger = logging.getLogger(__name__)


def load_lmps(
    actual_csv_path: Path | str,
    forecast_csv_path: Path | str,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Load actual and indicative LMPs from CSV files.

    Args:
        actual_csv_path: Path to actual LMP CSV with columns:
            interval_start_cpt, interval_end_cpt, lmp
        forecast_csv_path: Path to indicative LMP CSV with columns:
            as_of_cpt, interval_start_cpt, interval_end_cpt, horizon_5min_idx, lmp

    Returns:
        Tuple of (indicative_lmps, actual_lmps) DataFrames
    """
    actual_csv_path = Path(actual_csv_path)
    forecast_csv_path = Path(forecast_csv_path)

    logger.info(f"Loading actual LMPs from {actual_csv_path}")
    logger.info(f"Loading indicative LMPs from {forecast_csv_path}")

    actual_lmps = _load_actual_lmps(actual_csv_path)
    indicative_lmps = _load_indicative_lmps(forecast_csv_path)

    actual_lmps = ActualLmpSchema.validate(actual_lmps)
    indicative_lmps = IndicativeLmpSchema.validate(indicative_lmps)

    logger.info(
        f"Loaded {len(actual_lmps)} actual LMPs and {len(indicative_lmps)} indicative LMPs"
    )

    return indicative_lmps, actual_lmps


def _load_actual_lmps(csv_path: Path) -> pl.DataFrame:
    """
    Load actual LMPs from CSV.

    Input columns: interval_start_cpt, interval_end_cpt, lmp
    Output columns: interval_end_cpt (America/Chicago), lmp
    """
    df = pl.read_csv(csv_path)

    actual_lmps = (
        df.with_columns(
            interval_end_cpt=_parse_cpt_timestamp("interval_end_cpt"),
        )
        .select(["interval_end_cpt", "lmp"])
        .unique()
        .sort("interval_end_cpt")
    )

    return actual_lmps


def _load_indicative_lmps(csv_path: Path) -> pl.DataFrame:
    """
    Load indicative LMPs from CSV.

    Input columns: as_of_cpt, interval_start_cpt, interval_end_cpt, horizon_5min_idx, lmp
    Output columns: as_of_cpt (America/Chicago), interval_end_cpt (America/Chicago), horizon_5min_idx, lmp
    """
    df = pl.read_csv(csv_path)

    indicative_lmps = (
        df.with_columns(
            interval_end_cpt=_parse_cpt_timestamp("interval_end_cpt"),
            as_of_cpt=_parse_cpt_timestamp("as_of_cpt"),
            horizon_5min_idx=pl.col("horizon_5min_idx").cast(pl.Int32),
        )
        .select(["as_of_cpt", "interval_end_cpt", "horizon_5min_idx", "lmp"])
        .filter(pl.col("lmp").is_not_null())
        .filter(pl.col("horizon_5min_idx") >= 1)
        .filter(pl.col("horizon_5min_idx") <= NUM_INTERVALS)
        .unique()
        .sort(["as_of_cpt", "interval_end_cpt"])
    )

    return indicative_lmps


def _parse_cpt_timestamp(column_name: str) -> pl.Expr:
    """Parse a CPT timestamp string and set America/Chicago timezone."""
    return (
        pl.col(column_name)
        .str.to_datetime()
        .dt.replace_time_zone("America/Chicago")
    )
