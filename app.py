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


def run_manual_scan():
    """
    Run a one-off scan of all MARKETS and write signals.json.
    This is used by the 'Run new scan now' button.
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


@app.route("/refresh-live-signals", methods=["POST"])
def refresh_live_signals():
    """
    Endpoint used by the 'Run new scan now' button.
    Runs a manual scan and then reloads the live signals page.
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


if __name__ == "__main__":
    app.run()












