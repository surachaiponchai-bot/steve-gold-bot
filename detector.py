import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests

def fetch_gold_data():
    # Try 1: Yahoo Chart API direct (lightweight, no yfinance)
    try:
        print("Trying Yahoo Chart API GC=F...")
        # Yahoo chart endpoint
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=5m&range=2d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        print(f"Yahoo status {r.status_code}")
        j = r.json()
        # Parse
        result = j['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]
        closes = quotes['close']
        opens = quotes['open']
        highs = quotes['high']
        lows = quotes['low']
        # Build DF
        df = pd.DataFrame({
            'Close': closes,
            'Open': opens,
            'High': highs,
            'Low': lows
        }, index=pd.to_datetime(timestamps, unit='s'))
        df = df.dropna()
        if len(df) > 60:
            print(f"Yahoo OK: {len(df)} rows price {df['Close'].iloc[-1]}")
            return df
        else:
            print(f"Yahoo not enough {len(df)}")
    except Exception as e:
        print(f"Yahoo fail: {e}")
        import traceback; traceback.print_exc()

    # Try 2: Binance multiple endpoints
    endpoints = [
        "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=5m&limit=200",
        "https://data-api.binance.vision/api/v3/klines?symbol=PAXGUSDT&interval=5m&limit=200",
        "https://api1.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=5m&limit=200",
    ]
    for url in endpoints:
        try:
            print(f"Trying {url[:50]}...")
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
                print(f"Binance OK {url[:30]}: {len(df)} price {df['Close'].iloc[-1]}")
                return df
            else:
                print(f"Binance bad data {url}: {str(data)[:200]}")
        except Exception as e:
            print(f"Binance fail {url[:30]}: {e}")
            continue

    # Try 3: Coinbase
    try:
        print("Trying Coinbase PAXG-USD...")
        url = "https://api.exchange.coinbase.com/products/PAXG-USD/candles?granularity=300"
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 60:
            # coinbase: [time, low, high, open, close, volume]
            df = pd.DataFrame(data, columns=['Time','Low','High','Open','Close','Volume'])
            df = df.sort_values('Time')
            df['Datetime'] = pd.to_datetime(df['Time'], unit='s')
            df.set_index('Datetime', inplace=True)
            print(f"Coinbase OK: {len(df)} price {df['Close'].iloc[-1]}")
            return df
    except Exception as e:
        print(f"Coinbase fail: {e}")

    print("ALL FAILED - will retry in 60s")
    raise Exception("No data - all sources failed")

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
