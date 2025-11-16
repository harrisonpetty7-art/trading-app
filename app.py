from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime
import requests

# --- TELEGRAM NOTIFICATION (same as in bot_worker) ---

def send_telegram(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram not configured in environment variables.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": msg}

    try:
        requests.post(url, data=data)
        print("Telegram test message sent from app.py!")
    except Exception as e:
        print("Failed to send Telegram from app.py:", e)


app = Flask(__name__)

# -------------------------------------------------
# MARKETS CONFIG (LABEL, PLUS500 NAME, YAHOO SYMBOL)
# -------------------------------------------------
MARKETS = {
    # ----- INDICES -----
    "US100": {
        "label": "NASDAQ 100 / US Tech 100",
        "plus500": "US Tech 100",
        "yahoo": "^NDX",
    },
    "US500": {
        "label": "S&P 500 / US 500",
        "plus500": "US 500",
        "yahoo": "^GSPC",
    },
    "GER40": {
        "label": "Germany 40",
        "plus500": "Germany 40",
        "yahoo": "^GDAXI",
    },
    "UK100": {
        "label": "FTSE 100 / UK 100",
        "plus500": "UK 100",
        "yahoo": "^FTSE",
    },

    # ----- COMMODITIES -----
    "GOLD": {
        "label": "Gold",
        "plus500": "Gold",
        "yahoo": "GC=F",
    },
    "SILVER": {
        "label": "Silver",
        "plus500": "Silver",
        "yahoo": "SI=F",
    },
    "OIL": {
        "label": "US Crude Oil",
        "plus500": "Oil",
        "yahoo": "CL=F",
    },
    "OILB": {
        "label": "Brent Oil",
        "plus500": "Brent Oil",
        "yahoo": "BZ=F",
    },
    "NATGAS": {
        "label": "Natural Gas",
        "plus500": "Natural Gas",
        "yahoo": "NG=F",
    },

    # ----- FOREX (OPTIONAL, EASY TO FIND ON PLUS500) -----
    "EURUSD": {
        "label": "EUR/USD",
        "plus500": "EUR/USD",
        "yahoo": "EURUSD=X",
    },
    "GBPUSD": {
        "label": "GBP/USD",
        "plus500": "GBP/USD",
        "yahoo": "GBPUSD=X",
    },

    # ----- CRYPTO -----
    "BTCUSD": {
        "label": "Bitcoin / USD",
        "plus500": "Bitcoin",
        "yahoo": "BTC-USD",
    },
    "ETHUSD": {
        "label": "Ethereum / USD",
        "plus500": "Ethereum",
        "yahoo": "ETH-USD",
    },

    # ----- US STOCKS -----
    "AAPL": {
        "label": "Apple",
        "plus500": "Apple",
        "yahoo": "AAPL",
    },
    "TSLA": {
        "label": "Tesla",
        "plus500": "Tesla",
        "yahoo": "TSLA",
    },
    "MSFT": {
        "label": "Microsoft",
        "plus500": "Microsoft",
        "yahoo": "MSFT",
    },
    "AMZN": {
        "label": "Amazon",
        "plus500": "Amazon",
        "yahoo": "AMZN",
    },
    "NVDA": {
        "label": "NVIDIA",
        "plus500": "NVIDIA",
        "yahoo": "NVDA",
    },
}

# ------------------------
# BASIC PAGES / NAVIGATION
# ------------------------

@app.route("/")
def index():
    # Home screen – show markets list if you want it
    return render_template("index.html", markets=MARKETS)


@app.route("/account")
def account():
    # Simple placeholder for now so it never 500s
    return "<h1>Account page</h1><p>We’ll wire this up properly later.</p>"


@app.route("/backtest", methods=["GET", "POST"])
def backtest():
    """
    Simple backtest: download data for one symbol, compute an equity curve,
    and pass it to the template. This is deliberately simple so it doesn't break.
    """
    error = None
    results = None
    chart_url = None

    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            error = "Please choose a market."
            return render_template(
                "backtest.html",
                error=error,
                results=results,
                chart_url=chart_url,
                markets=MARKETS,
            )

        market = MARKETS.get(symbol, {})
        yahoo = market.get("yahoo", symbol)

        try:
            df = yf.download(yahoo, period="1y", interval="1d", progress=False)
        except Exception as e:
            error = f"Error downloading data for {yahoo}: {e}"
            return render_template(
                "backtest.html",
                error=error,
                results=results,
                chart_url=chart_url,
                markets=MARKETS,
            )

        if df is None or df.empty:
            error = "No data for that symbol."
            return render_template(
                "backtest.html",
                error=error,
                results=results,
                chart_url=chart_url,
                markets=MARKETS,
            )

        df["Return"] = df["Close"].pct_change()
        df["Equity"] = (1 + df["Return"]).cumprod()

        total_return = float(df["Equity"].iloc[-1] - 1) * 100.0
        results = {
            "symbol": symbol,
            "label": market.get("label", symbol),
            "total_return": round(total_return, 2),
        }

        # Make a simple equity curve chart
        fig, ax = plt.subplots()
        df["Equity"].plot(ax=ax)
        ax.set_title(f"Equity curve for {symbol}")
        ax.set_ylabel("Equity (start = 1.0)")
        fig.tight_layout()

        # Save chart into static folder
        img_path = os.path.join("static", "backtest_equity.png")
        fig.savefig(img_path)
        plt.close(fig)
        chart_url = "/static/backtest_equity.png"

    return render_template(
        "backtest.html",
        error=error,
        results=results,
        chart_url=chart_url,
        markets=MARKETS,
    )


@app.route("/results")
def results():
    # If your results.html expects more, we can add later.
    return render_template("results.html")


# -------------------------
# LIVE SIGNALS + MANUAL SCAN
# -------------------------

@app.route("/live-signals")
def live_signals():
    error = None
    raw_signals = []

    # Try to read the file written by bot_worker.py or by manual refresh
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

@app.route("/test-alert", methods=["POST"])
def test_alert():
    # Send a simple test message
    send_telegram("Test alert from your trading bot app ✅")
    # Go back to the live signals page
    return redirect(url_for("live_signals"))


def run_manual_scan():
    """
    Run a one-off scan of all MARKETS and write signals.json.
    This is used by the 'Run new scan now' button.
    Logic is similar to the background worker.
    """
    results = []

    for key, info in MARKETS.items():
        yahoo = info.get("yahoo")
        if not yahoo:
            continue

        print(f"[manual scan] Downloading {key} ({yahoo})...")
        try:
            df = yf.download(yahoo, period="6mo", interval="1h", progress=False)
        except Exception as e:
            print(f"[manual scan] Error downloading {yahoo}: {e}")
            continue

        if df is None or df.empty or len(df) < 60:
            print(f"[manual scan] Not enough data for {yahoo}, skipping.")
            continue

        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()
        df = df.dropna()
        if len(df) < 2:
            continue

        short_now = float(df["SMA20"].iloc[-1])
        long_now = float(df["SMA50"].iloc[-1])
        short_prev = float(df["SMA20"].iloc[-2])
        long_prev = float(df["SMA50"].iloc[-2])
        price_now = float(df["Close"].iloc[-1])

        trend = "flat"
        signal = "none"
        message = "No clear trend."

        if short_now > long_now:
            trend = "up"
            message = "Uptrend; look for buys."
            if short_prev <= long_prev:
                signal = "BUY"
                message = "NEW BUY signal (short MA crossed ABOVE long MA)."
        elif short_now < long_now:
            trend = "down"
            message = "Downtrend; look for sells."
            if short_prev >= long_prev:
                signal = "SELL"
                message = "NEW SELL signal (short MA crossed BELOW long MA)."

        results.append({
            "symbol": key,
            "trend": trend,
            "signal": signal,
            "message": message,
            "price": price_now,
            "short_ma": short_now,
            "long_ma": long_now,
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        })

    try:
        with open("signals.json", "w") as f:
            json.dump(results, f)
        print("[manual scan] signals.json updated.")
    except Exception as e:
        print(f"[manual scan] Error writing signals.json: {e}")


@app.route("/refresh-live-signals", methods=["GET", "POST"])
def refresh_live_signals():
    """
    Endpoint used by the 'Run new scan now' button.
    Runs a manual scan and then reloads the live signals page.

    We allow both GET and POST so it works whether the button is a link
    or a form submit.
    """
    run_manual_scan()
    return redirect(url_for("live_signals"))

@app.route("/api/live-signals")
def api_live_signals():
    """Return raw signals.json as JSON for the frontend to poll."""
    try:
        with open("signals.json", "r") as f:
            raw_signals = json.load(f)
    except FileNotFoundError:
        return jsonify({"signals": [], "error": "No signals yet"}), 200
    except Exception as e:
        return jsonify({"signals": [], "error": str(e)}), 500

    return jsonify({"signals": raw_signals, "error": None}), 200


# -------------
# ENTRY POINT
# -------------
if __name__ == "__main__":
    # For local testing; on Render, gunicorn runs this.
    app.run(host="0.0.0.0", port=5000, debug=False)



















