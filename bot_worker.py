import yfinance as yf
import json
import time
import os
import requests
from datetime import datetime

# ----- TELEGRAM NOTIFICATION FUNCTION -----
def send_telegram(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram not configured in environment variables.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": msg}

    try:
        requests.post(url, data=data, timeout=10)
        print("Telegram message sent!")
    except Exception as e:
        print("Failed to send Telegram:", e)


# ----- MARKETS TO WATCH -----
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

    # US stocks
    "AAPL": "AAPL",
    "TSLA": "TSLA",
    "MSFT": "MSFT",
    "AMZN": "AMZN",
    "NVDA": "NVDA",
}


# ----- CHECK A SINGLE MARKET -----
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

    # Need at least 2 rows for previous/now
    if len(df) < 2:
        print(f"Not enough data for {symbol}")
        return None

    short_now = float(df["SMA20"].iloc[-1])
    long_now = float(df["SMA50"].iloc[-1])
    short_prev = float(df["SMA20"].iloc[-2])
    long_prev = float(df["SMA50"].iloc[-2])
    price_now = float(df["Close"].iloc[-1])

    trend = "none"
    signal = "none"
    message = "No clear trend."

    # ---- Trend + signals ----
    if short_now > long_now:
        trend = "up"
        message = "Uptrend in place (BUY / avoid sells)."

        # New BUY signal only when crossing from below to above
        if short_prev <= long_prev:
            signal = "BUY"
            message = "NEW BUY trend signal (short MA crossed above long MA)."
            send_telegram(
                f"BUY signal on {symbol}! Price: {round(price_now, 4)}"
            )

    elif short_now < long_now:
        trend = "down"
        message = "Downtrend in place (SELL / avoid longs)."

        # New SELL signal only when crossing from above to below
        if short_prev >= long_prev:
            signal = "SELL"
            message = "NEW SELL trend signal (short MA crossed below long MA)."
            send_telegram(
                f"SELL signal on {symbol}! Price: {round(price_now, 4)}"
            )

    # Return a dict used by the website
    return {
        "symbol": symbol,
        "trend": trend,
        "signal": signal,
        "price": price_now,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }


# ----- MAIN LOOP -----
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

        # Save for the web app
        with open("signals.json", "w") as f:
            json.dump(results, f)

        print("Scan complete. Sleeping for 5 minutes...\n")
        time.sleep(300)


if __name__ == "__main__":
    main_loop()
