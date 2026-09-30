import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
import yfinance as yf
from datetime import datetime

def fetch_gold_data(symbol="GC=F", period="2d", interval="5m"):
    # 1. Try yfinance first (many tickers)
    tickers = ["GC=F", "XAUUSD=X", "PAXG-USD", "GOLD", "GLD"]
    for t in tickers:
        try:
            print(f"Trying yfinance {t}...")
            df = yf.download(t, period=period, interval=interval, progress=False, auto_adjust=True, threads=False)
            if df is not None and len(df) > 50:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                print(f"yfinance success {t}: {len(df)}")
                return df
        except Exception as e:
            print(f"yfinance {t} fail: {e}")
            continue

    # 2. Fallback: Binance PAXGUSDT (gold pegged token) - free API, not blocked
    try:
        print("Trying Binance PAXGUSDT...")
        # 5m candles, need ~ 53*2 = 106 candles for safety
        url = "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=5m&limit=200"
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 60:
            # Binance format: [open time, open, high, low, close, volume, ...]
            df = pd.DataFrame(data, columns=['OpenTime','Open','High','Low','Close','Volume','CloseTime','QuoteVol','Trades','TBBase','TBQuote','Ignore'])
            df['Close'] = df['Close'].astype(float)
            df['Open'] = df['Open'].astype(float)
            df['High'] = df['High'].astype(float)
            df['Low'] = df['Low'].astype(float)
            # make index time
            df['Datetime'] = pd.to_datetime(df['OpenTime'], unit='ms')
            df.set_index('Datetime', inplace=True)
            print(f"Binance success: {len(df)} rows, last price {df['Close'].iloc[-1]}")
            return df
    except Exception as e:
        print(f"Binance fail: {e}")

    # 3. Last fallback: create fake trending data so bot doesn't crash, but mark
    print("ALL SOURCES FAILED - returning empty to retry")
    raise Exception("No gold data")

def generate_chart_image_53(df, path, result):
    try:
        plt.figure(figsize=(10,4))
        plt.plot(df['Close'].values, color='#FFD700', linewidth=2)
        plt.title(f"Steve Gold 53 - Sim {result.get('similarity',0):.0f}% Peak@{result.get('peak_position',0)} Price {df['Close'].iloc[-1]:.2f}")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"Chart saved {path}")
    except Exception as e:
        print(f"Chart error: {e}")
        # create empty image
        plt.figure(); plt.text(0.5,0.5,"Chart error"); plt.savefig(path); plt.close()
