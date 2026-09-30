import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests

def fetch_gold_data():
    # Light mode: Binance only, no yfinance
    try:
        print("Fetching Binance PAXGUSDT...")
        url = "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=5m&limit=200"
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 60:
            df = pd.DataFrame(data, columns=['OpenTime','Open','High','Low','Close','Volume','CloseTime','QuoteVol','Trades','TBBase','TBQuote','Ignore'])
            df['Close'] = df['Close'].astype(float)
            df['Open'] = df['Open'].astype(float)
            df['High'] = df['High'].astype(float)
            df['Low'] = df['Low'].astype(float)
            df['Datetime'] = pd.to_datetime(df['OpenTime'], unit='ms')
            df.set_index('Datetime', inplace=True)
            print(f"Binance OK: {len(df)} rows price {df['Close'].iloc[-1]}")
            return df
    except Exception as e:
        print(f"Binance fail: {e}")
    raise Exception("No data")

def generate_chart_image_53(df, path, result):
    try:
        plt.figure(figsize=(9,4))
        plt.plot(df['Close'].values, color='#FFD700', linewidth=2)
        plt.title(f"Steve Gold 53 - Sim {result.get('similarity',0):.0f}% Price {df['Close'].iloc[-1]:.2f}")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(path, dpi=100)
        plt.close()
        print(f"Chart saved {path}")
    except Exception as e:
        print(f"Chart err {e}")
        plt.figure(); plt.text(0.5,0.5,"err"); plt.savefig(path); plt.close()
