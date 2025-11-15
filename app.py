from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import uuid
import os
import json          # <— add this line
from datetime import datetime

app = Flask(__name__)

# --------------------------
# Simple in-memory account
# --------------------------

ACCOUNT = {
    "balance": 100000.0,
    "history": []
}

def record(action, amount):
    ACCOUNT["history"].append({
        "id": str(uuid.uuid4()),
        "action": action,
        "amount": amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

# --------------------------
# Markets for Signals (Plus500-friendly)
# --------------------------
# left side: what you choose in the app
# 'yahoo': ticker used for data
# 'plus500': how you’d trade it on Plus500

MARKETS = {
    "NAS100": {
        "label": "NASDAQ 100 / US Tech 100",
        "yahoo": "^NDX",
        "plus500": "US Tech 100"
    },
    "SPX500": {
        "label": "S&P 500 / US 500",
        "yahoo": "^GSPC",
        "plus500": "US 500"
    },
    "UK100": {
        "label": "FTSE 100 / UK 100",
        "yahoo": "^FTSE",
        "plus500": "UK 100"
    },
    "GER40": {
        "label": "Germany 40",
        "yahoo": "^GDAXI",
        "plus500": "Germany 40"
    },
    "GOLD": {
        "label": "Gold (XAU/USD)",
        "yahoo": "XAUUSD=X",
        "plus500": "Gold"
    },
    "EURUSD": {
        "label": "EUR/USD",
        "yahoo": "EURUSD=X",
        "plus500": "EUR/USD"
    },
    "GBPUSD": {
        "label": "GBP/USD",
        "yahoo": "GBPUSD=X",
        "plus500": "GBP/USD"
    }
}

# --------------------------
# Routes
# --------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        form_type = request.form.get("type")
        amount = float(request.form.get("amount"))

        if form_type == "deposit":
            ACCOUNT["balance"] += amount
            record("Deposit", amount)

        if form_type == "withdraw":
            amount = min(amount, ACCOUNT["balance"])
            ACCOUNT["balance"] -= amount
            record("Withdraw", amount)

        return redirect(url_for("account"))

    return render_template("account.html", account=ACCOUNT)

@app.route("/backtest", methods=["GET", "POST"])
def backtest():
    if request.method == "POST":
        ticker = request.form.get("ticker")
        short = int(request.form.get("short"))
        long = int(request.form.get("long"))
        start = request.form.get("start")
        end = request.form.get("end")

        df = yf.download(ticker, start=start, end=end, progress=False)

        df["SMA_short"] = df["Close"].rolling(short).mean()
        df["SMA_long"] = df["Close"].rolling(long).mean()
        df["signal"] = (df["SMA_short"] > df["SMA_long"]).astype(int)
        df["position_change"] = df["signal"].diff().fillna(0)

        balance = ACCOUNT["balance"]
        position = 0
        equity_curve = []

        for index, row in df.iterrows():
            price = row["Close"]
            pc = row["position_change"]

            if pc == 1 and position == 0:
                position = balance / price
                balance = 0
            elif pc == -1 and position > 0:
                balance = position * price
                position = 0

            equity_curve.append(balance + position * price)

        df["equity"] = equity_curve

        img_path = f"static/equity_{uuid.uuid4()}.png"
        plt.figure(figsize=(8,4))
        plt.plot(df["equity"])
        plt.title("Equity Curve")
        plt.tight_layout()
        plt.savefig(img_path)
        plt.close()

        return render_template("results.html", img=img_path, ticker=ticker)

    return render_template("backtest.html")

# --------------------------
# Trend Signals route
# --------------------------

@app.route("/signals", methods=["GET", "POST"])
def signals():
    result = None
    error = None

    if request.method == "POST":
        market_key = request.form.get("market")
        if market_key not in MARKETS:
            error = "Unknown market selection."
        else:
            info = MARKETS[market_key]
            yahoo_symbol = info["yahoo"]

            try:
                # Get recent daily data
                df = yf.download(yahoo_symbol, period="6mo", interval="1d", progress=False)
            except Exception as e:
                df = None
                error = f"Data download failed: {e}"

            if df is None or df.empty:
                error = error or "No data returned for this market."
            else:
                # Trend-following: 20 / 50 SMA
                short = 20
                long = 50
                df["SMA_short"] = df["Close"].rolling(short).mean()
                df["SMA_long"] = df["Close"].rolling(long).mean()
                df = df.dropna()

                if len(df) < 2:
                    error = "Not enough data for trend calculation."
                else:
                    # Take the last two values explicitly as floats
                    short_now = float(df["SMA_short"].iloc[-1])
                    long_now = float(df["SMA_long"].iloc[-1])
                    short_prev = float(df["SMA_short"].iloc[-2])
                    long_prev = float(df["SMA_long"].iloc[-2])
                    price_now = float(df["Close"].iloc[-1])

                    trend = "none"
                    signal = "none"
                    message = "No clear trend."

                    if short_now > long_now:
                        trend = "up"
                        message = "Uptrend in place (BUY bias)."
                        if short_prev <= long_prev:
                            signal = "buy"
                            message = "NEW BUY trend signal (short MA crossed above long MA)."
                    elif short_now < long_now:
                        trend = "down"
                        message = "Downtrend in place (SELL / avoid longs)."
                        if short_prev >= long_prev:
                            signal = "sell"
                            message = "NEW SELL trend signal (short MA crossed below long MA)."

                    result = {
                        "market_key": market_key,
                        "label": info["label"],
                        "plus500_name": info["plus500"],
                        "yahoo_symbol": yahoo_symbol,
                        "price": round(price_now, 4),
                        "short_ma": round(short_now, 4),
                        "long_ma": round(long_now, 4),
                        "trend": trend,
                        "signal": signal,
                        "message": message
                    }

return render_template("signals.html", markets=MARKETS, result=result, error=error)


@app.route("/live-signals")
def live_signals():
    error = None
    raw_signals = []

    # Try to read the file written by bot_worker.py
    try:
        with open("signals.json", "r") as f:
            raw_signals = json.load(f)
    except FileNotFoundError:
        error = "No signals yet. The bot may still be running its first scan."
    except Exception as e:
        error = f"Could not read signals: {e}"

    # Enrich signals with labels and Plus500 names if we have them
    enriched = []
    for row in raw_signals:
        key = row.get("symbol")
        info = MARKETS.get(key, {})
        enriched.append({
            "symbol": key,
            "label": info.get("label", key),
            "plus500_name": info.get("plus500", key),
            "signal": row.get("signal"),
            "price": row.get("price"),
            "time": row.get("time"),
        })

    return render_template("live_signals.html", signals=enriched, error=error)


if __name__ == "__main__":
    app.run()



