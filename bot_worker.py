import yfinance as yf
import json
import time
import os
import requests   # <---- this must be added

# ---- TELEGRAM NOTIFICATION FUNCTION ----
def send_telegram(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram not configured")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": msg}

    try:
        requests.post(url, data=data)
        print("Telegram message sent!")
    except Exception as e:
        print("Failed to send Telegram:", e)


WATCHLIST = {
    # Indices
    "US100": "^NDX",
    "US500": "^GSPC",
    "GER40": "^GDAXI",
    "UK100": "^FTSE",

    # Commodities
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "OIL": "CL=F",
    "OILB": "BZ=F",
    "NATGAS": "NG=F",

    # Forex
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",

    # Crypto
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",

    # US Stocks
    "AAPL": "AAPL",
    "TSLA": "TSLA",
    "MSFT": "MSFT",
    "AMZN": "AMZN",
    "NVDA": "NVDA",
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
