import time
import yfinance as yf
import json
from datetime import datetime

WATCHLIST = {
    "NAS100": "^NDX",
    "SPX500": "^GSPC",
    "GER40": "^GDAXI",
    "UK100": "^FTSE",
    "GOLD": "GC=F",          # <— changed here
    "OIL": "CL=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X"
}


def check_market(symbol, yahoo):
    df = yf.download(yahoo, period="3mo", interval="1h", progress=False)
    if df.empty:
        return None
    
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df = df.dropna()
    
    short_now = df["SMA20"].iloc[-1]
    long_now = df["SMA50"].iloc[-1]
    short_prev = df["SMA20"].iloc[-2]
    long_prev = df["SMA50"].iloc[-2]
    
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
        all_signals = []
        
        for symbol, yahoo in WATCHLIST.items():
            result = check_market(symbol, yahoo)
            if result:
                print(result)
                all_signals.append(result)
        
        with open("signals.json", "w") as f:
            json.dump(all_signals, f, indent=2)
        
        time.sleep(300)

if __name__ == "__main__":
    main_loop()
