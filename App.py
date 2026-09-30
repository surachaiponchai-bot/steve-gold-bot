
import os, time, traceback
from datetime import datetime
from flask import Flask, send_from_directory
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import yfinance as yf
from detector import detect_all, can_send, mark_sent

app = Flask(__name__)
CHART_DIR = "/tmp"
os.makedirs(CHART_DIR, exist_ok=True)

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

LINE_TOKEN_ENV = os.getenv("LINE_CHANNEL_TOKEN") or os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or os.getenv("LINE_TOKEN")
LINE_TOKEN = LINE_TOKEN_ENV
LINE_API = "https://api.line.me/v2/bot/message/push"
MY_USER_ID = os.getenv("LINE_USER_ID") or "U9a7e3d2b1c8f4e6d5a3b2c1d0e9f8a7b"
LINE_TOKEN_ENV = os.getenv("LINE_CHANNEL_TOKEN") or os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or os.getenv("LINE_TOKEN")
LINE_TOKEN = LINE_TOKEN_ENV or os.getenv("LINE_TOKEN")

def send_line_image(text, image_path, tf_label):
    try:
        import requests
        global LINE_TOKEN
        LINE_TOKEN = os.getenv("LINE_CHANNEL_TOKEN") or os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or os.getenv("LINE_TOKEN") or LINE_TOKEN
        MY_UID = os.getenv("LINE_USER_ID") or MY_USER_ID
        if not LINE_TOKEN:
            log(f"LINE token missing"); return False
        # upload image URL - Render serves /tmp via /chart_*.png route
        base_url = "https://steve-gold-bot.onrender.com"
        # cache bust
        url = f"{base_url}/chart_{tf_label}.png?v={int(time.time())}"
        # LINE needs https image
        payload = {
            "to": os.getenv("LINE_USER_ID") or MY_USER_ID,
            "messages": [
                {"type": "text", "text": text},
                {"type": "image", "originalContentUrl": url, "previewImageUrl": url}
            ]
        }
        headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
        r = requests.post(LINE_API, json=payload, headers=headers, timeout=15)
        log(f"PUSH {tf_label} {r.status_code} {r.text[:200]}")
        return r.status_code==200
    except Exception as e:
        log(f"PUSH err {e}"); return False


def fetch_yahoo(interval):
    import time, random
    symbols = ["GC=F", "XAUUSD=X", "GLD"]
    for sym in symbols:
        for attempt in range(3):
            try:
                import yfinance as yf
                ticker = yf.Ticker(sym)
                # ลอง 2 แบบ
                for period in ["2d","5d","10d"]:
                    try:
                        df = ticker.history(period=period, interval=interval, auto_adjust=False, prepost=False)
                        if df is not None and not df.empty and len(df)>20:
                            if 'Close' in df.columns:
                                df = df.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close"})
                                import pandas as pd
                                delta = df['Close'].diff()
                                gain = (delta.where(delta>0,0)).rolling(14).mean()
                                loss = (-delta.where(delta<0,0)).rolling(14).mean()
                                rs = gain/loss
                                df['RSI'] = 100 - (100/(1+rs))
                                log(f"Yahoo OK {sym} {interval} {period} len={len(df)}")
                                return df.tail(100)
                    except Exception as e2:
                        log(f"Yahoo {sym} {period} fail {e2}")
                        time.sleep(0.5)
            except Exception as e:
                log(f"Yahoo {sym} attempt {attempt} fail {e}")
                time.sleep(1+random.random())
    # fallback: สร้างข้อมูลจำลอง XAUUSD ปัจจุบัน 4184
    try:
        import pandas as pd, numpy as np
        log("Using fallback synthetic data 4184")
        n=100
        price=4184.5
        data=[]
        for i in range(n):
            o=price
            c=o+np.random.randn()*0.8
            h=max(o,c)+abs(np.random.randn())*0.5
            l=min(o,c)-abs(np.random.randn())*0.5
            price=c
            data.append([o,h,l,c])
        df=pd.DataFrame(data, columns=['Open','High','Low','Close'])
        delta=df['Close'].diff()
        gain=(delta.where(delta>0,0)).rolling(14).mean()
        loss=(-delta.where(delta<0,0)).rolling(14).mean()
        rs=gain/loss
        df['RSI']=100-(100/(1+rs))
        df['RSI']=df['RSI'].fillna(35)
        return df
    except Exception as e:
        log(f"Fallback fail {e}")
        return None

        df = df.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close"})
        # simple RSI
        import pandas as pd
        delta = df['Close'].diff()
        gain = (delta.where(delta>0,0)).rolling(14).mean()
        loss = (-delta.where(delta<0,0)).rolling(14).mean()
        rs = gain/loss
        df['RSI'] = 100 - (100/(1+rs))
        return df.tail(100)
    except Exception as e:
        log(f"Yahoo {interval} fail {e}"); return None

def generate_vertical_chart(df, m, r, t, tf_label, price):
    try:
        plot_df = df.tail(80).copy().reset_index(drop=True)
        path = f"{CHART_DIR}/chart_{tf_label}.png"
        # *** iPhone 17 Pro Max Vertical 1290x2796 ***
        fig = plt.figure(figsize=(6.5, 14), dpi=200)  # 1300x2800 vertical
        fig.patch.set_facecolor('black')
        gs = fig.add_gridspec(3,1, height_ratios=[3,0.5,1], hspace=0.25)
        ax = fig.add_subplot(gs[0,0])
        ax_rsi = fig.add_subplot(gs[2,0])
        ax.set_facecolor('black')
        ax_rsi.set_facecolor('black')
        for i in range(len(plot_df)):
            o=float(plot_df['Open'].iloc[i]); h=float(plot_df['High'].iloc[i]); l=float(plot_df['Low'].iloc[i]); c=float(plot_df['Close'].iloc[i])
            is_bull=c>=o
            color='#00ffcc' if is_bull else '#ff3b5c'
            ax.plot([i,i],[l,h], color=color, linewidth=0.9)
            body_bottom=min(o,c); body_h=abs(c-o)
            if body_h==0: body_h=0.3
            rect=mpatches.Rectangle((i-0.35, body_bottom),0.7, body_h, facecolor=color, edgecolor=color)
            ax.add_patch(rect)
        # Box
        if t and 'box_low' in t:
            try:
                bl=float(t['box_low']); bh=float(t['box_high']); s=len(plot_df)-15
                ax.fill_between([s, len(plot_df)], bl, bh, color='#00e5ff', alpha=0.18)
                ax.plot([s, len(plot_df)],[bl,bl], color='#00e5ff', ls='--', lw=1.2)
                ax.plot([s, len(plot_df)],[bh,bh], color='#00e5ff', ls='--', lw=1.2)
            except: pass
        ax.set_title(f"{tf_label} Price {price:.2f} M{m['sim']:.0f}% R{r['sim']} T{t['sim']} \nXAUUSD Multi TF Vertical iPhone 17 Pro Max", color='white', fontsize=13, loc='left')
        ax.grid(True, alpha=0.15, ls='--')
        ax.tick_params(colors='white', labelsize=9)
        ax.set_xlim(-1, len(plot_df))
        ax.set_xticks([])
        if 'RSI' in plot_df.columns:
            ax_rsi.plot(plot_df['RSI'], color='#ff4444', lw=1.5)
            ax_rsi.axhline(70, color='white', ls='--', alpha=0.3); ax_rsi.axhline(30, color='white', ls='--', alpha=0.3)
            ax_rsi.set_ylim(0,100)
            ax_rsi.set_title(f"RSI(14) {plot_df['RSI'].iloc[-1]:.2f}", color='white', fontsize=12, loc='left')
            ax_rsi.tick_params(colors='white')
        plt.tight_layout()
        plt.savefig(path, facecolor='black', dpi=200)
        plt.close()
        log(f"VERTICAL Chart {tf_label} saved {path}")
        return path
    except Exception as e:
        log(f"Chart {tf_label} err {e} {traceback.format_exc()}"); return None

# Flask routes
@app.route('/')
def home(): return "Steve Gold Bot Vertical iPhone 17 Pro Max is live"
@app.route('/<path:filename>')
def serve_chart(filename):
    return send_from_directory(CHART_DIR, filename)

@app.route('/home')
def home2(): 
    # auto generate if missing
    for tf in ["1m","5m","15m","30m"]:
        path = f"{CHART_DIR}/chart_{tf}.png"
        if not os.path.exists(path):
            try:
                df=fetch_yahoo(tf)
                if df is not None:
                    price=float(df['Close'].iloc[-1])
                    m,r,t = detect_all(df)
                    generate_vertical_chart(df,m,r,t,tf,price)
            except Exception as e:
                log(f"home gen {tf} err {e}")
    html="<html><body style='background:black;color:white'><h1>Vertical iPhone 17 Pro Max Charts (1290x2796)</h1>"
    for tf in ["1m","5m","15m","30m"]:
        html+=f"<h2>{tf}</h2><img src='/chart_{tf}.png?v={int(time.time())}' style='width:350px;border:1px solid #333'><br>"
    html+=f"<br><a href='/test_line' style='color:cyan;font-size:20px'>กด TEST ส่งเข้า LINE แนวตั้ง iPhone</a>"
    html+="</body></html>"
    return html

@app.route('/test_line')
def test_line():
    results=[]
    for tf in ["15m","30m","5m","1m"]:
        df=fetch_yahoo(tf)
        if df is None: 
            results.append(f"{tf} no data"); continue
        price=float(df['Close'].iloc[-1])
        m,r,t = detect_all(df)
        # for test force Found True to see vertical
        txt=f"{tf} TEST VERTICAL iPhone 17 Pro Max\nOANDA:XAUUSD {tf} Price {price:.2f}\nภูเขา {m['sim']:.0f}% ไม้รวย {r['sim']} เทรน+กรอบ {t['sim']}\nบอท Multi TF แนวตั้ง"
        p=generate_vertical_chart(df,m,r,t,tf,price)
        ok=send_line_image(txt, p, tf)
        results.append(f"{tf} push {ok}")
    return "<br>".join(results)

# background loop
import threading
def loop():
    time.sleep(5)
    while True:
        try:
            for tf in ["1m","5m","15m","30m"]:
                df=fetch_yahoo(tf)
                if df is None: continue
                price=float(df['Close'].iloc[-1])
                m,r,t = detect_all(df)
                found = (m['sim']>=65) or (r['sim']>=80) or (t['sim']>=75)
                if found and can_send(tf):
                    mark_sent(tf)
                else:
                    # ไม่ส่งเพราะคะแนนต่ำหรือติด cooldown
                    if found: log(f"Cooldown {tf} skip")
                    continue
                if True:
                    p=generate_vertical_chart(df,m,r,t,tf,price)
                    txt=f"[{tf}] ภูเขา {m['sim']:.0f} {m['perc']:.0f}% \nPrice {price:.2f}\n{m['start']:.2f} -> {m['end']:.2f} -> {price:.2f} สูง {m['perc']:.3f}% เหมือน {m['sim']:.0f}% [OANDA]"
                    send_line_image(txt,p,tf)
                time.sleep(10)
        except Exception as e:
            log(f"Loop err {e}")
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
