from pathlib import Path

import pandas as pd
import polars as pl
from plotnine import (
    aes,
    element_text,
    facet_wrap,
    geom_line,
    ggplot,
    ggsave,
    labs,
    scale_color_manual,
    theme,
    theme_minimal,
)


def plot_single_backtest(
    results_df: pl.DataFrame,
    output_path: Path,
    title: str = "Backtest Results",
    subtitle: str | None = None,
    width: float = 7,
    height: float = 5,
) -> None:
    """
    Create multi-facet plot for a single backtest run.
    """

    df = results_df.to_pandas()

    price_data = df[["interval_end_cpt", "price_actual"]].copy()
    price_data["panel"] = "Price ($/MWh)"

    pnl_data = df[["interval_end_cpt", "cumu_net_pnl_usd"]].copy().reset_index(drop=True)
    pnl_data["panel"] = "Cumulative PnL ($)"

    soc_data = df[["interval_end_cpt", "soc_end_mwh"]].copy().reset_index(drop=True)
    soc_data["panel"] = "State of Charge (MWh)"

    combined_data = []

    for _, row in price_data.iterrows():
        combined_data.append(
            {
                "interval_end_cpt": row["interval_end_cpt"],
                "value": row["price_actual"],
                "series": "price_actual",
                "panel": "Price ($/MWh)",
            }
        )

    for _, row in pnl_data.iterrows():
        combined_data.append(
            {
                "interval_end_cpt": row["interval_end_cpt"],
                "value": row["cumu_net_pnl_usd"],
                "series": "pnl",
                "panel": "Cumulative PnL ($)",
            }
        )

    for _, row in soc_data.iterrows():
        combined_data.append(
            {
                "interval_end_cpt": row["interval_end_cpt"],
                "value": row["soc_end_mwh"],
                "series": "soc",
                "panel": "State of Charge (MWh)",
            }
        )

    combined_df = pd.DataFrame(combined_data)
    plot = (
        ggplot(combined_df, aes(x="interval_end_cpt", y="value"))
        + geom_line(aes(color="series"), size=0.8)
        + scale_color_manual(values=["#003049", "#d62828", "#f77f00"])
        + facet_wrap("~ panel", ncol=1, scales="free_y")
        + labs(
            title=title,
            subtitle=subtitle,
            x="Time",
            y="",
        )
        + theme_minimal()
        + theme(
            figure_size=(width, height),
            axis_text_x=element_text(rotation=45, hjust=1),
            strip_text=element_text(weight="bold", size=10),
            legend_position="none",
        )
    )

    ggsave(plot, filename=str(output_path), dpi=300, verbose=False)
