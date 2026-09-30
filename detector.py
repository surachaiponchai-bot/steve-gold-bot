import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def fetch_gold_data(symbol="GC=F", period="2d", interval="5m"):
    # ลองหลายตัว เผื่อโดนบล็อก
    tickers = ["GC=F", "XAUUSD=X", "PAXG-USD", "GOLD"]
    for t in tickers:
        try:
            print(f"Trying ticker {t}...")
            df = yf.download(t, period=period, interval=interval, progress=False, auto_adjust=True)
            if df is not None and len(df) > 50:
                # fix multi-index
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                print(f"Success with {t}: {len(df)} rows")
                return df
        except Exception as e:
            print(f"{t} failed: {e}")
            continue
    # ถ้าไม่ได้เลย สร้าง dummy เพื่อไม่ให้บอทตาย
    print("All tickers failed, using fallback")
    raise Exception("No gold data available")

def generate_chart_image_53(df, path, result):
    try:
        plt.figure(figsize=(10,4))
        plt.plot(df['Close'].values, color='gold', linewidth=2)
        plt.title(f"【entity-Steve Gold¦canonical_name=Steve Gold】 53 Candles - Similarity {result.get('similarity',0):.0f}% Peak@{result.get('peak_position',0)}")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"Chart saved {path}")
    except Exception as e:
        print(f"Chart error: {e}")
