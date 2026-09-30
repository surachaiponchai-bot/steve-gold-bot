
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def fetch_gold_data(symbol="GC=F", period="2d", interval="5m"):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    df = df.dropna()
    return df

def generate_chart_image_53(df_53, path, result=None):
    closes = df_53['Close'].values
    fig, ax = plt.subplots(figsize=(10,4), dpi=150)
    ax.plot(closes, color='#f5c518', linewidth=2, label='XAUUSD 53 candles')
    
    # วาดเส้นภูเขาในอุดมคติ
    if result:
        # จุดต่ำสุดเริ่ม ท้าย และพีคกลาง
        start_idx = np.argmin(df_53['Low'].values[:15]) if 'Low' in df_53.columns else 0
        end_idx = 38 + np.argmin(df_53['Low'].values[38:]) if 'Low' in df_53.columns else 52
        peak_idx = 15 + np.argmax(df_53['High'].values[15:38]) if 'High' in df_53.columns else np.argmax(closes)
        
        ax.scatter([start_idx, peak_idx, end_idx], 
                   [closes[start_idx], closes[peak_idx], closes[end_idx]], 
                   color='cyan', s=60, zorder=5)
        ax.plot([start_idx, peak_idx, end_idx],
                [closes[start_idx], closes[peak_idx], closes[end_idx]],
                color='lime', linestyle='--', linewidth=1.5, label=f"Mountain {result['similarity']:.0f}%")
    
    ax.set_title(f"53 Candles Mountain - {result['description'] if result else ''}", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, facecolor='black')
    plt.close()
    print(f"Chart saved to {path}")
    return path
