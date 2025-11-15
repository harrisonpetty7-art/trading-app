from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import uuid
import os
from datetime import datetime

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run()
