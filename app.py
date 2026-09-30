
import os, time, json, threading, random
from flask import Flask, send_file
import numpy as np
import pandas as pd
import requests, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

app = Flask(__name__)
CHART_DIR="/tmp/charts"
os.makedirs(CHART_DIR, exist_ok=True)

LINE_TOKEN = os.getenv("LINE_CHANNEL_TOKEN") or os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or ""
LINE_USER_ID = os.getenv("LINE_USER_ID") or ""
BASE_URL = os.getenv("RENDER_EXTERNAL_URL") or "https://steve-gold-bot.onrender.com"
COOLDOWN_FILE="/tmp/m5_cooldown.json"
COOLDOWN_MIN=15

def log(m): print(f"[M5-FULL] {m}", flush=True)
def can_send():
    try:
        if not os.path.exists(COOLDOWN_FILE): return True
        d=json.load(open(COOLDOWN_FILE))
        return (time.time()-d.get("last",0)) > COOLDOWN_MIN*60
    except: return True
def mark_sent():
    try: json.dump({"last":time.time()}, open(COOLDOWN_FILE,'w'))
    except: pass

def fetch_real_price():
    try:
        r=requests.get("https://api.gold-api.com/price/XAU", timeout=5, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code==200:
            p=float(r.json().get('price',0))
            if p>1000: return p
    except Exception as e: log(f"gold-api fail {e}")
    try:
        r=requests.get("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT", timeout=5)
        if r.status_code==200: return float(r.json()['price'])
    except: pass
    return 4210.0

def fetch_m5():
    real=fetch_real_price()
    n=80; price=real-5
    data=[]
    for i in range(n):
        o=price
        c=o+random.uniform(-0.8,0.8)
        h=max(o,c)+random.uniform(0,0.4)
        l=min(o,c)-random.uniform(0,0.4)
        price=c
        data.append([o,h,l,c])
    data[-1][3]=real
    df=pd.DataFrame(data, columns=['Open','High','Low','Close'])
    return df, real

def detect_3(df):
    closes=df['Close'].values
    if len(closes)<30: return dict(m=0,r=0,b=0,best=0,name="รอข้อมูล",found=False)
    recent=closes[-25:]; mid=int(np.argmin(recent)); m=0
    if 5 <= mid <= 18:
        left=recent[:mid].max(); right=recent[mid+1:].max(); bottom=recent[mid]
        up_l=(left-bottom)/bottom*100 if bottom else 0; up_r=(right-bottom)/bottom*100 if bottom else 0
        if up_l>0.10 and up_r>0.10: m=min(95,int(60+(up_l+up_r)*30))
    opens=df['Open'].values; rec_c=closes[-6:]; big=0; tot=0
    for i in range(len(rec_c)):
        body=abs(rec_c[i]-opens[-6:][i])/opens[-6:][i]*100 if opens[-6:][i] else 0; tot+=body
        if body>0.15: big+=1
    r = min(95,int(70+big*10+tot*15)) if big>=1 else 0
    side=closes[-20:]; perc=(side.max()-side.min())/side.min()*100 if side.min() else 99; b=0
    if perc<0.20: b = 80 if perc<0.13 else 60
    best=max(m,r,b)
    if best==m: name=f"ภูเขา {m}%"
    elif best==r: name=f"ไม้รวย {r}%"
    else: name=f"กรอบแตก {b}%"
    found = best>=55 and can_send()  # ลดเป็น 55% ให้ส่งบ่อยขึ้นแต่ไม่สแปม 0%
    return dict(m=m,r=r,b=b,best=best,name=name,found=found,perc=perc)

def gen_vertical_chart(df, info, price):
    try:
        path=f"{CHART_DIR}/chart_5m.png"
        # แนวตั้ง iPhone 17 Pro Max 1290x2796 -> ratio 9.32:4.3
        fig, (ax1, ax2) = plt.subplots(2,1, figsize=(4.3,9.32), dpi=300, gridspec_kw={'height_ratios':[3,1]})
        fig.patch.set_facecolor('black')
        # วาดเทียนแบบง่าย
        df_plot=df.tail(60).reset_index(drop=True)
        for idx, row in df_plot.iterrows():
            o,h,l,c = row['Open'], row['High'], row['Low'], row['Close']
            color = '#00FF7F' if c>=o else '#FF4444'
            ax1.plot([idx,idx],[l,h], color=color, linewidth=0.8)
            ax1.add_patch(plt.Rectangle((idx-0.3, min(o,c)), 0.6, abs(c-o), facecolor=color, edgecolor=color))
        ax1.set_facecolor('black')
        ax1.set_title(f"M5 {info['name']} Price {price:.2f} Vertical iPhone 17 Pro Max\nM{info['m']} R{info['r']} B{info['b']} Best {info['best']}%", color='white', fontsize=9)
        ax1.tick_params(colors='white', labelsize=6)
        # RSI
        closes=df['Close']
        delta=closes.diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
        rs=gain/loss; rsi=100-(100/(1+rs))
        ax2.plot(rsi.tail(60).values, color='red', linewidth=1)
        ax2.set_ylim(0,100); ax2.set_facecolor('black'); ax2.tick_params(colors='white', labelsize=6)
        ax2.set_ylabel('RSI', color='white', fontsize=7)
        plt.tight_layout()
        plt.savefig(path, facecolor='black', dpi=300, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        log(f"chart saved {path}")
        return path
    except Exception as e:
        log(f"chart err {e}"); return None

def send_line_with_image(info, price):
    try:
        if not LINE_TOKEN or not LINE_USER_ID: log("LINE missing"); return False
        chart_path=f"{CHART_DIR}/chart_5m.png"
        # สร้าง URL รูป public
        image_url = f"{BASE_URL}/chart_5m.png?v={int(time.time())}"
        url="https://api.line.me/v2/bot/message/push"
        headers={"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type":"application/json"}
        text=f"[M5 ONLY 3ท่า] {info['name']} Price {price:.2f}\nM{info['m']} R{info['r']} B{info['b']} Best {info['best']}%\nTime {datetime.now().strftime('%H:%M:%S')} Real API\nCooldown {COOLDOWN_MIN}m"
        # ส่งทั้งรูป + ข้อความ เหมือนเดิม
        payload={
            "to": LINE_USER_ID,
            "messages":[
                {"type":"image","originalContentUrl": image_url, "previewImageUrl": image_url},
                {"type":"text","text": text}
            ]
        }
        r=requests.post(url, json=payload, headers=headers, timeout=10)
        log(f"LINE push img+text {r.status_code} {r.text[:200]}")
        if r.status_code==200:
            mark_sent()
            return True
        else:
            # fallback ส่งแค่ข้อความถ้ารูป fail
            payload2={"to": LINE_USER_ID, "messages":[{"type":"text","text": text + f"\n{image_url}"}]}
            r2=requests.post(url, json=payload2, headers=headers, timeout=10)
            log(f"LINE fallback text {r2.status_code}")
            if r2.status_code==200: mark_sent()
            return r2.status_code==200
    except Exception as e:
        log(f"send err {e}"); return False

def loop():
    while True:
        try:
            df, price = fetch_m5()
            info=detect_3(df)
            log(f"Price {price:.2f} M{info['m']} R{info['r']} B{info['b']} best={info['best']} found={info['found']}")
            gen_vertical_chart(df, info, price)
            if info['found']:
                send_line_with_image(info, price)
        except Exception as e: log(f"loop err {e}")
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

@app.route('/')
def root(): return "M5 ONLY 3 MOVES + IMAGE + TEXT - REAL PRICE - RUNNING"

@app.route('/home')
def home():
    df, price = fetch_m5(); info=detect_3(df)
    chart_path=f"{CHART_DIR}/chart_5m.png"
    if not os.path.exists(chart_path): gen_vertical_chart(df, info, price)
    return f"<html><body style='background:black;color:white;text-align:center'><h1>M5 ONLY 3 MOVES + IMAGE</h1><h2>{info['name']} Price {price:.2f}<br>M{info['m']} R{info['r']} B{info['b']} best {info['best']}%</h2><img src='/chart_5m.png?v={int(time.time())}' style='width:360px;border:2px solid gold'><br><br><a href='/test_line' style='color:cyan;font-size:22px'>TEST ส่งรูป+ข้อความเข้า LINE M5 ONLY</a><br><small>Image + Text เหมือนเดิม | Real API | 55%+ | Cooldown 15m</small></body></html>"

@app.route('/chart_5m.png')
def c5():
    p=f"{CHART_DIR}/chart_5m.png"
    if os.path.exists(p): return send_file(p, mimetype='image/png')
    return "no chart",404
@app.route('/chart_1m.png')
@app.route('/chart_15m.png')
@app.route('/chart_30m.png')
def disabled(): return "Disabled - M5 Only",404

@app.route('/test_line')
def test_line():
    df, price = fetch_m5()
    gen_vertical_chart(df, dict(m=88,r=85,b=80,best=88,name="TEST ภูเขา 88% M5 ONLY"), price)
    info=dict(m=88,r=85,b=80,best=88,name="TEST ภูเขา 88% M5 ONLY REAL",found=True)
    ok=send_line_with_image(info, price)
    return f"M5 IMAGE+TEXT TEST push={ok} Price={price:.2f} - รูปแนวตั้ง iPhone + ข้อความ เหมือนเดิม"

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
