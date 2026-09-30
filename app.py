
import os, time, json, threading
from flask import Flask, send_file
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd
import requests
from datetime import datetime

app = Flask(__name__)
CHART_DIR="/tmp/charts"
os.makedirs(CHART_DIR, exist_ok=True)

LINE_TOKEN = os.getenv("LINE_CHANNEL_TOKEN") or os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or ""
LINE_USER_ID = os.getenv("LINE_USER_ID") or ""
COOLDOWN_FILE="/tmp/m5_cooldown.json"
COOLDOWN_MIN=15

def log(m): print(f"[M5-ONLY] {m}", flush=True)

def can_send():
    try:
        if not os.path.exists(COOLDOWN_FILE): return True
        d=json.load(open(COOLDOWN_FILE))
        return (time.time()-d.get("last",0)) > COOLDOWN_MIN*60
    except: return True

def mark_sent():
    try: json.dump({"last":time.time()}, open(COOLDOWN_FILE,'w'))
    except: pass

def fetch_m5():
    for sym in ["GC=F","XAUUSD=X","GLD"]:
        try:
            df=yf.Ticker(sym).history(period="5d", interval="5m", auto_adjust=False)
            if df is not None and len(df)>50:
                log(f"M5 OK {sym} len={len(df)}")
                return df
        except Exception as e:
            log(f"fetch {sym} fail {e}")
    log("Fallback M5 4185")
    n=100; price=4185.0; data=[]
    for i in range(n):
        o=price; c=o+np.random.randn()*0.6
        h=max(o,c)+abs(np.random.randn())*0.3; l=min(o,c)-abs(np.random.randn())*0.3
        price=c; data.append([o,h,l,c,1000])
    return pd.DataFrame(data, columns=['Open','High','Low','Close','Volume'])

def detect_3(df):
    try:
        closes=df['Close'].values
        if len(closes)<30:
            return dict(m=0,r=0,b=0,best=0,name="รอข้อมูล",found=False)
        recent=closes[-25:]; mid=int(np.argmin(recent))
        m=0
        if 5 <= mid <= 18:
            left=recent[:mid].max(); right=recent[mid+1:].max(); bottom=recent[mid]
            up_l=(left-bottom)/bottom*100 if bottom else 0
            up_r=(right-bottom)/bottom*100 if bottom else 0
            if up_l>0.12 and up_r>0.12:
                m=min(95, int(65 + (up_l+up_r)*35))
        opens=df['Open'].values[-6:] if 'Open' in df.columns else closes[-6:]
        rec_c=closes[-6:]; big=0; tot=0
        for i in range(len(rec_c)):
            body=abs(rec_c[i]-opens[i])/opens[i]*100 if opens[i] else 0
            tot+=body
            if body>0.18: big+=1
        r = min(95, int(75+big*10+tot*20)) if big>=2 else 0
        side=closes[-20:]; perc=(side.max()-side.min())/side.min()*100 if side.min() else 99
        b=0
        if perc<0.18:
            last=side[-1]; prev=np.mean(side[-6:-1])
            brk=abs(last-prev)/prev*100 if prev else 0
            b = 85 if perc<0.12 and brk>0.08 else (75 if perc<0.12 else 60)
            if brk<0.03: b=max(0,b-20)
        best=max(m,r,b)
        if best==m: name=f"ภูเขา {m}%"
        elif best==r: name=f"ไม้รวย {r}%"
        else: name=f"กรอบแตก {b}%"
        found = best>=65 and can_send()
        return dict(m=m,r=r,b=b,best=best,name=name,found=found,perc=perc if 'perc' in locals() else 0)
    except Exception as e:
        log(f"detect err {e}")
        return dict(m=0,r=0,b=0,best=0,name="error",found=False)

def gen_chart(df,info,price):
    try:
        path=f"{CHART_DIR}/chart_5m.png"
        fig=mpf.figure(figsize=(4.3,9.32), dpi=300)
        ax=fig.add_subplot(2,1,1)
        ax2=fig.add_subplot(2,1,2, sharex=ax)
        df_plot=df.tail(60)
        mpf.plot(df_plot, type='candle', ax=ax, volume=False, style='yahoo', tight_layout=True, show_nontrading=False)
        ax.set_title(f"M5 {info['name']} Price {price:.2f} Vertical iPhone", fontsize=9, color='white')
        fig.patch.set_facecolor('black'); ax.set_facecolor('black'); ax2.set_facecolor('black')
        delta=df['Close'].diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
        rs=gain/loss; rsi=100-(100/(1+rs))
        ax2.plot(rsi.tail(60).values, color='red', linewidth=0.8)
        ax2.set_ylim(0,100)
        plt.savefig(path, facecolor='black', dpi=300, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        log(f"chart saved {path}")
        return path
    except Exception as e:
        log(f"gen err {e}")
        return None

def send_line(info,price):
    try:
        if not LINE_TOKEN or not LINE_USER_ID:
            log("LINE missing"); return False
        url="https://api.line.me/v2/bot/message/push"
        headers={"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type":"application/json"}
        text=f"[M5 ONLY 3ท่า] {info['name']} Price {price:.2f} M{info['m']} R{info['r']} B{info['b']} - {datetime.now().strftime('%H:%M:%S')}"
        payload={"to": LINE_USER_ID, "messages":[{"type":"text","text": text}]}
        r=requests.post(url, json=payload, headers=headers, timeout=10)
        log(f"LINE push {r.status_code}")
        if r.status_code==200: mark_sent()
        return r.status_code==200
    except Exception as e:
        log(f"send err {e}"); return False

def loop():
    while True:
        try:
            df=fetch_m5()
            if df is None: time.sleep(60); continue
            price=float(df['Close'].iloc[-1])
            info=detect_3(df)
            log(f"Price {price:.2f} M{info['m']} R{info['r']} B{info['b']} best={info['best']} found={info['found']}")
            gen_chart(df,info,price)
            if info['found']:
                send_line(info,price)
        except Exception as e:
            log(f"loop err {e}")
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

@app.route('/')
def root(): return "M5 ONLY 3 MOVES - RUNNING"

@app.route('/home')
def home():
    df=fetch_m5(); price=float(df['Close'].iloc[-1]); info=detect_3(df)
    p=f"{CHART_DIR}/chart_5m.png"
    if not os.path.exists(p): gen_chart(df,info,price)
    return f"<html><body style='background:black;color:white;text-align:center'><h1>M5 ONLY 3 MOVES</h1><h2>{info['name']} Price {price:.2f}<br>M{info['m']} R{info['r']} B{info['b']}</h2><img src='/chart_5m.png?v={int(time.time())}' style='width:350px;border:2px solid gold'><br><br><a href='/test_line' style='color:cyan'>TEST M5 ONLY</a><br>Cooldown 15min | >=65% only</body></html>"

@app.route('/chart_5m.png')
def c5():
    p=f"{CHART_DIR}/chart_5m.png"
    if os.path.exists(p): return send_file(p, mimetype='image/png')
    return "no chart",404

@app.route('/chart_1m.png')
@app.route('/chart_15m.png')
@app.route('/chart_30m.png')
def disabled():
    return "Disabled - M5 Only",404

@app.route('/test_line')
def test_line():
    df=fetch_m5(); price=float(df['Close'].iloc[-1])
    info=dict(m=88,r=85,b=80,best=88,name="TEST ภูเขา 88%",found=True)
    gen_chart(df,info,price)
    ok=send_line(info,price)
    return f"M5 ONLY TEST push={ok} Price={price:.2f} - Cooldown 15min >=65% only"

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
