# Stock SMA/EMA Analysis

Automatically fetches **5 years** of historical price data for a configurable list of stock tickers and computes **20 / 50 / 100 / 200-day Simple Moving Averages (SMA)** and **Exponential Moving Averages (EMA)** for each. Results are saved to a single combined CSV file and committed back to this repository daily.

---

## Stocks Tracked

Tickers are listed in [`stocks.txt`](stocks.txt) — one symbol per line:

```
AAPL
MSFT
GOOGL
AMZN
TSLA
NVDA
META
```

To add or remove stocks, simply edit `stocks.txt`.

---

## Output

All results are written to [`output/results.csv`](output/results.csv) with the following columns:

| Column | Description |
|---|---|
| `Ticker` | Stock symbol |
| `Date` | Trading date |
| `Open` | Opening price |
| `High` | Daily high |
| `Low` | Daily low |
| `Close` | Closing price (adjusted) |
| `Volume` | Daily volume |
| `SMA_20` | 20-day Simple Moving Average |
| `SMA_50` | 50-day Simple Moving Average |
| `SMA_100` | 100-day Simple Moving Average |
| `SMA_200` | 200-day Simple Moving Average |
| `EMA_20` | 20-day Exponential Moving Average |
| `EMA_50` | 50-day Exponential Moving Average |
| `EMA_100` | 100-day Exponential Moving Average |
| `EMA_200` | 200-day Exponential Moving Average |

---

## Project Structure

```
stock-sma-ema/
├── .github/
│   └── workflows/
│       └── daily_analysis.yml   ← GitHub Actions cron workflow
├── output/
│   └── results.csv              ← Auto-generated combined output
├── stocks.txt                   ← Ticker list (one per line)
├── sma_ema_analysis.py          ← Main analysis script
├── requirements.txt             ← Python dependencies
└── README.md
```

---

## Running Locally

### Prerequisites

- Python 3.11+
- pip

### Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/stock-sma-ema.git
cd stock-sma-ema

# Install dependencies
pip install -r requirements.txt

# Run the analysis
python sma_ema_analysis.py
```

Results will be saved to `output/results.csv`.

---

## GitHub Actions — Automated Daily Run

The workflow is defined in [`.github/workflows/daily_analysis.yml`](.github/workflows/daily_analysis.yml).

### Schedule

| Timezone | Time | Days |
|---|---|---|
| **PST (UTC-7)** | **8:00 PM** | Monday – Friday |
| UTC | 3:00 AM (next day) | Tuesday – Saturday |

Cron expression: `0 3 * * 2-6`

### What the workflow does

1. **Checkout** the repository
2. **Set up Python 3.11**
3. **Install** dependencies from `requirements.txt`
4. **Run** `sma_ema_analysis.py` — fetches latest data and recomputes all indicators
5. **Commit & push** `output/results.csv` back to the repo (only if data changed)

### Manual trigger

You can also trigger the workflow manually from the **Actions** tab in GitHub → select **Daily Stock SMA/EMA Analysis** → click **Run workflow**.

### Permissions

The workflow uses the built-in `GITHUB_TOKEN` secret (automatically provided by GitHub) with `contents: write` permission to push the updated CSV. No additional secrets are required.

---

## Dependencies

| Package | Purpose |
|---|---|
| [`yfinance`](https://github.com/ranaroussi/yfinance) | Fetch historical OHLCV data from Yahoo Finance |
| [`pandas`](https://pandas.pydata.org/) | Data manipulation, rolling/ewm calculations |
| [`numpy`](https://numpy.org/) | Numerical support |

---

## License

MIT
