from fastapi import FastAPI
import yfinance as yf
import pandas as pd

app = FastAPI()

def download_data(symbol: str):
    data = yf.download(symbol, period="max", interval="1d")
    if data.empty:
        raise ValueError(f"No data found for {symbol}")
    return data

def get_valid_last_date(data):
    last_date = data.index.max()
    while last_date not in data.index:
        last_date -= pd.Timedelta(days=1)
    return last_date

def filter_range(data, range_key: str):
    range_key = range_key.lower()
    last_date = get_valid_last_date(data)

    if range_key == "d":
        start = last_date - pd.Timedelta(days=7)
        return data.loc[data.index >= start]

    elif range_key == "m":
        start = last_date - pd.Timedelta(days=30)
        subset = data.loc[data.index >= start]
        return subset if not subset.empty else data.tail(22)

    elif range_key == "y":
        start = last_date - pd.Timedelta(days=365)
        subset = data.loc[data.index >= start]
        return subset if not subset.empty else data.tail(252)

    elif range_key == "x":
        return data

    else:
        raise ValueError("Invalid range key. Use: d, m, y, x")

def build_response(symbol, subset):
    closes = subset["Close"]
    
    return {
        "symbol": symbol.upper(),
        "dates": [d.strftime("%Y-%m-%d") for d in subset.index],
        "prices": [float(v) for v in closes]
    }

@app.get("/")
def home():
    return {"status": "chart data api running"}

@app.get("/chart/{symbol}/{range_key}")
def chart(symbol: str, range_key: str):
    try:
        data = download_data(symbol)
        subset = filter_range(data, range_key)
        return build_response(symbol, subset)
    except Exception as e:
        return {"error": str(e)}
