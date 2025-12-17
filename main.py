from fastapi import FastAPI
import yfinance as yf
import pandas as pd

app = FastAPI()


# ================================
#   INTERNAL DATA FUNCTIONS
# ================================
def download_data(symbol: str):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="max", interval="1d", auto_adjust=False)

    if hist is None or not isinstance(hist, pd.DataFrame) or len(hist) == 0:
        raise ValueError(f"No data available for {symbol}")

    # Close kolonunu garanti altına al
    if "Close" not in hist.columns:
        for cand in ["close", "adjclose", "Adj Close", "AdjClose"]:
            if cand in hist.columns:
                hist["Close"] = hist[cand]
                break

    if "Close" not in hist.columns:
        raise ValueError("Close column missing even after fallback")

    # Index datetime olmalı
    if not isinstance(hist.index, pd.DatetimeIndex):
        hist.index = pd.to_datetime(hist.index, errors="coerce")

    hist = hist[pd.notna(hist.index)]

    return hist


def safe_subset(df, fallback):
    if df is None or len(df) == 0:
        return fallback
    return df


def filter_range(data, range_key):
    last_date = data.index.max()

    if pd.isna(last_date):
        return data.tail(30)

    rk = range_key.lower()

    if rk == "d":
        return safe_subset(data.loc[data.index >= last_date - pd.Timedelta(days=7)], data.tail(7))

    if rk == "m":
        return safe_subset(data.loc[data.index >= last_date - pd.Timedelta(days=30)], data.tail(22))

    if rk == "y":
        return safe_subset(data.loc[data.index >= last_date - pd.Timedelta(days=365)], data.tail(252))

    if rk == "x":
        return data

    raise ValueError("Range must be one of: d, m, y, x")


def extract_chart_data(symbol, range_key):
    data = download_data(symbol)
    subset = filter_range(data, range_key)

    closes = pd.to_numeric(subset["Close"], errors="coerce")
    closes = closes.fillna(method="ffill").fillna(method="bfill")

    dates = [d.strftime("%Y-%m-%d") for d in subset.index]

    return {
        "symbol": symbol.upper(),
        "range": range_key,
        "dates": dates,
        "prices": [float(v) for v in closes]
    }


# ================================
#         FASTAPI ENDPOINTS
# ================================

@app.get("/")
def home():
    return {"status": "chart api running"}


@app.get("/chart/{symbol}/{range_key}")
def chart(symbol: str, range_key: str):
    try:
        result = extract_chart_data(symbol, range_key)
        return result
    except Exception as e:
        return {"error": str(e)}
