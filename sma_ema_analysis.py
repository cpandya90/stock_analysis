"""
Stock SMA/EMA Analysis
======================
Reads tickers from stocks.txt, fetches 5 years of historical OHLCV data
via yfinance, computes 20/50/100/200-day SMA and EMA for each ticker,
saves all results into a single combined CSV (output/results.csv), and
generates one PNG chart per ticker (output/charts/<TICKER>.png) showing
the closing price overlaid with 20/50/200-day SMA and EMA lines.

Schedule: Runs daily at 8 PM PST via GitHub Actions.
"""

import os
import sys
import logging
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — required for GitHub Actions / headless servers
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
STOCKS_FILE   = "stocks.txt"
OUTPUT_DIR    = "output"
OUTPUT_FILE   = os.path.join(OUTPUT_DIR, "results.csv")
CHARTS_DIR    = os.path.join(OUTPUT_DIR, "charts")
HISTORY_PERIOD = "5y"
SMA_EMA_WINDOWS = [20, 50, 100, 200]

# Indicators to show on the chart (subset of SMA_EMA_WINDOWS)
CHART_WINDOWS = [20, 50, 200]

# Colour palette for chart lines
CHART_COLORS = {
    "Close":   "#1f77b4",   # steel blue
    "SMA_20":  "#ff7f0e",   # orange
    "SMA_50":  "#2ca02c",   # green
    "SMA_200": "#d62728",   # red
    "EMA_20":  "#ff7f0e",   # orange  (dashed)
    "EMA_50":  "#2ca02c",   # green   (dashed)
    "EMA_200": "#d62728",   # red     (dashed)
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_tickers(filepath: str) -> list[str]:
    """Read ticker symbols from a text file (one per line)."""
    if not os.path.exists(filepath):
        logger.error(f"Stocks file not found: {filepath}")
        sys.exit(1)

    with open(filepath, "r") as f:
        tickers = [line.strip().upper() for line in f if line.strip()]

    if not tickers:
        logger.error(f"No tickers found in {filepath}")
        sys.exit(1)

    logger.info(f"Loaded {len(tickers)} ticker(s): {', '.join(tickers)}")
    return tickers


def fetch_history(ticker: str, period: str = HISTORY_PERIOD) -> pd.DataFrame:
    """Download historical OHLCV data for a single ticker via yfinance."""
    logger.info(f"  Fetching {period} history for {ticker} ...")
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            logger.warning(f"  No data returned for {ticker}. Skipping.")
            return pd.DataFrame()

        # Flatten MultiIndex columns if present (yfinance >=0.2 behaviour)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index.name = "Date"
        df.reset_index(inplace=True)
        df["Ticker"] = ticker
        logger.info(f"  {ticker}: {len(df)} rows retrieved.")
        return df
    except Exception as exc:
        logger.error(f"  Failed to fetch data for {ticker}: {exc}")
        return pd.DataFrame()


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add SMA and EMA columns for each window in SMA_EMA_WINDOWS."""
    close = df["Close"]
    for window in SMA_EMA_WINDOWS:
        df[f"SMA_{window}"] = close.rolling(window=window, min_periods=window).mean()
        df[f"EMA_{window}"] = close.ewm(span=window, adjust=False).mean()
    return df


def build_combined_dataframe(tickers: list[str]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    Fetch data and compute indicators for all tickers.
    Returns:
        combined  — single DataFrame with all tickers stacked
        per_stock — dict mapping ticker → its individual DataFrame
    """
    frames: list[pd.DataFrame] = []
    per_stock: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        df = fetch_history(ticker)
        if df.empty:
            continue
        df = compute_indicators(df)
        per_stock[ticker] = df.copy()
        frames.append(df)

    if not frames:
        logger.error("No data was retrieved for any ticker. Exiting.")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)

    # Reorder columns: Ticker, Date, OHLCV, then indicators
    ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
    indicator_cols = (
        [f"SMA_{w}" for w in SMA_EMA_WINDOWS]
        + [f"EMA_{w}" for w in SMA_EMA_WINDOWS]
    )
    col_order = ["Ticker", "Date"] + ohlcv_cols + indicator_cols
    col_order = [c for c in col_order if c in combined.columns]
    combined = combined[col_order]
    combined.sort_values(["Ticker", "Date"], inplace=True)
    combined.reset_index(drop=True, inplace=True)

    return combined, per_stock


def save_results(df: pd.DataFrame, filepath: str) -> None:
    """Save the combined DataFrame to CSV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False, float_format="%.4f")
    logger.info(
        f"Results saved to {filepath}  "
        f"({len(df):,} rows, {df['Ticker'].nunique()} tickers)"
    )


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

def generate_chart(ticker: str, df: pd.DataFrame, charts_dir: str) -> None:
    """
    Generate a price + SMA/EMA chart for one ticker and save as PNG.

    Layout:
      - Top panel  : Close price + SMA 20/50/200 (solid) + EMA 20/50/200 (dashed)
      - Bottom panel: Volume bar chart
    """
    os.makedirs(charts_dir, exist_ok=True)

    dates = pd.to_datetime(df["Date"])

    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1,
        figsize=(16, 9),
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True,
    )
    fig.patch.set_facecolor("#0d1117")   # dark background (GitHub-style)
    for ax in (ax_price, ax_vol):
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#c9d1d9", labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

    # --- Price panel ---
    ax_price.plot(
        dates, df["Close"],
        color=CHART_COLORS["Close"], linewidth=1.4, label="Close", zorder=5,
    )

    for w in CHART_WINDOWS:
        sma_col = f"SMA_{w}"
        ema_col = f"EMA_{w}"
        color = CHART_COLORS.get(sma_col, "#aaaaaa")

        if sma_col in df.columns:
            ax_price.plot(
                dates, df[sma_col],
                color=color, linewidth=1.0, linestyle="-",
                label=f"SMA {w}", alpha=0.85,
            )
        if ema_col in df.columns:
            ax_price.plot(
                dates, df[ema_col],
                color=color, linewidth=1.0, linestyle="--",
                label=f"EMA {w}", alpha=0.85,
            )

    ax_price.set_title(
        f"{ticker}  —  Close Price with SMA/EMA (20 / 50 / 200-day)  |  "
        f"5-Year History  |  Generated {datetime.utcnow().strftime('%Y-%m-%d UTC')}",
        color="#c9d1d9", fontsize=11, pad=10,
    )
    ax_price.set_ylabel("Price (USD)", color="#c9d1d9", fontsize=9)
    ax_price.yaxis.set_label_position("right")
    ax_price.yaxis.tick_right()
    ax_price.grid(color="#21262d", linewidth=0.5, linestyle="--")

    legend = ax_price.legend(
        loc="upper left", fontsize=8,
        facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9",
        ncol=4,
    )

    # --- Volume panel ---
    vol = df["Volume"].fillna(0)
    # Colour bars green/red based on daily price direction
    close_arr = df["Close"].values
    bar_colors = [
        "#3fb950" if i == 0 or close_arr[i] >= close_arr[i - 1] else "#f85149"
        for i in range(len(close_arr))
    ]
    ax_vol.bar(dates, vol, color=bar_colors, width=1.5, alpha=0.7)
    ax_vol.set_ylabel("Volume", color="#c9d1d9", fontsize=9)
    ax_vol.yaxis.set_label_position("right")
    ax_vol.yaxis.tick_right()
    ax_vol.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x/1e6:.0f}M" if x >= 1e6 else f"{x/1e3:.0f}K")
    )
    ax_vol.grid(color="#21262d", linewidth=0.5, linestyle="--")

    # --- X-axis formatting ---
    ax_vol.xaxis.set_major_locator(mdates.YearLocator())
    ax_vol.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_vol.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
    plt.setp(ax_vol.xaxis.get_majorticklabels(), color="#c9d1d9", fontsize=9)

    plt.tight_layout(pad=1.5)

    out_path = os.path.join(charts_dir, f"{ticker}.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info(f"  Chart saved: {out_path}")


def generate_all_charts(per_stock: dict[str, pd.DataFrame], charts_dir: str) -> None:
    """Generate PNG charts for every ticker."""
    logger.info(f"Generating charts → {charts_dir}/")
    for ticker, df in per_stock.items():
        try:
            generate_chart(ticker, df, charts_dir)
        except Exception as exc:
            logger.error(f"  Chart generation failed for {ticker}: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info(
        f"Stock SMA/EMA Analysis  —  "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    logger.info("=" * 60)

    tickers = load_tickers(STOCKS_FILE)
    combined_df, per_stock = build_combined_dataframe(tickers)
    save_results(combined_df, OUTPUT_FILE)
    generate_all_charts(per_stock, CHARTS_DIR)

    logger.info("Analysis complete.")


if __name__ == "__main__":
    main()
