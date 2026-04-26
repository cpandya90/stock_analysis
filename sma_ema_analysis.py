"""
Stock SMA/EMA Analysis
======================
Reads tickers from stocks.txt, fetches 5 years of historical OHLCV data
via yfinance, computes 20/50/100/200-day SMA and EMA for each ticker,
and saves all results into a single combined CSV: output/results.csv.

Schedule: Runs daily at 8 PM PST via GitHub Actions.
"""

import os
import sys
import logging
from datetime import datetime

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
STOCKS_FILE = "stocks.txt"
OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "results.csv")
HISTORY_PERIOD = "5y"
SMA_EMA_WINDOWS = [20, 50, 100, 200]

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
# Helpers
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


def build_combined_dataframe(tickers: list[str]) -> pd.DataFrame:
    """Fetch data and compute indicators for all tickers; return combined DataFrame."""
    frames = []
    for ticker in tickers:
        df = fetch_history(ticker)
        if df.empty:
            continue
        df = compute_indicators(df)
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
    # Keep only columns that actually exist (safety guard)
    col_order = [c for c in col_order if c in combined.columns]
    combined = combined[col_order]

    # Sort by Ticker then Date
    combined.sort_values(["Ticker", "Date"], inplace=True)
    combined.reset_index(drop=True, inplace=True)
    return combined


def save_results(df: pd.DataFrame, filepath: str) -> None:
    """Save the combined DataFrame to CSV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False, float_format="%.4f")
    logger.info(f"Results saved to {filepath}  ({len(df):,} rows, {df['Ticker'].nunique()} tickers)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info(f"Stock SMA/EMA Analysis  —  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)

    tickers = load_tickers(STOCKS_FILE)
    combined_df = build_combined_dataframe(tickers)
    save_results(combined_df, OUTPUT_FILE)

    logger.info("Analysis complete.")


if __name__ == "__main__":
    main()
