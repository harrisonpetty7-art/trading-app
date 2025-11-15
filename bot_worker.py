import time
import yfinance as yf
import json
from datetime import datetime

WATCHLIST = {
    "NAS100": "^NDX",
    "SPX500": "^GSPC",
    "GER40": "^GDAXI",
    "UK100": "^FTSE",
    "GOLD": "GC=F",        # <— fixed
    "OIL": "CL=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X"
}


def check_market(symbol, yahoo):
    try:
        df = yf.download(yahoo, period="3mo", interval="1h", progress=False)
    except Exception as e:
        print(f"Error downloading {yahoo}: {e}")
        return None

    if df is None or df.empty:
        print(f"No data for {yahoo}, skipping.")
        return None

    # Moving averages
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df = df.dropna()

    short_now = float(df["SMA20"].iloc[-1])
    long_now = float(df["SMA50"].iloc[-1])
    short_prev = float(df["SMA20"].iloc[-2])
    long_prev = float(df["SMA50"].iloc[-2])

    signal = "none"

    if short_now > long_now and short_prev <= long_prev:
        signal = "BUY"
    elif short_now < long_now and short_prev >= long_prev:
        signal = "SELL"

    return {
        "symbol": symbol,
        "signal": signal,
        "price": float(df["Close"].iloc[-1]),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }


def main_loop():
    while True:
        print("\n--- Running bot scan ---")

        results = []

        for symbol, yahoo in WATCHLIST.items():
            print(f"Scanning {symbol} ({yahoo})...")
            data = check_market(symbol, yahoo)
            if data:
                results.append(data)
                print(data)

        with open("signals.json", "w") as f:
            json.dump(results, f)

        print("Scan complete. Sleeping for 5 minutes...\n")
        time.sleep(300)


if __name__ == "__main__":
    main_loop()
