import os, time, json, threading, random
from flask import Flask, request, send_file, jsonify
import pandas as pd, requests, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
app = Flask(__name__)
CHART_DIR="/tmp/charts"
os.makedirs(CHART_DIR, exist_ok=True)
LINE_TOKEN=os.getenv("LINE_CHANNEL_TOKEN") or ""
LINE_USER_ID=os.getenv("LINE_USER_ID") or ""
BASE_URL=os.getenv("RENDER_EXTERNAL_URL") or "https://steve-gold-bot.onrender.com"
COOLDOWN_FILE="/tmp/ruay_cooldown.json"
def log(m): print(f"[RUAY ONLY] {m}", flush=True)
def can_send():
    try:
        if not os.path.exists(COOLDOWN_FILE): return True
        return (time.time()-json.load(open(COOLDOWN_FILE)).get("last",0))>300
    except: return True
def mark_sent():
    json.dump({"last":time.time()}, open(COOLDOWN_FILE,'w'))
def fetch_m5():
    price=4174.53
    try:
        r=requests.get("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT", timeout=5)
        if r.status_code==200: price=float(r.json()['price'])
    except: pass
    try:
        r=requests.get("https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=5m&limit=80", timeout=8)
        if r.status_code==200:
            kl=r.json()
            data=[[float(k[1]),float(k[2]),float(k[3]),float(k[4])] for k in kl]
            df=pd.DataFrame(data, columns=['Open','High','Low','Close'])
            return df, float(kl[-1][4])
    except: pass
    data=[]; cur=price-12
    for i in range(80):
        o=cur
        if i==75:
            c=o+random.uniform(2.5,5.0); h=c+0.3; l=o-random.uniform(3,7)
        else:
            c=o+random.uniform(-1.2,1.2); h=max(o,c)+0.5; l=min(o,c)-0.5
        data.append([o,h,l,c]); cur=c
    return pd.DataFrame(data, columns=['Open','High','Low','Close']), price

def detect_ruay(df):
    closes=df['Close']
    rsi=100-(100/(1+(closes.diff().where(lambda x:x>0,0).rolling(14).mean() / -closes.diff().where(lambda x:x<0,0).rolling(14).mean())))
    last_rsi=float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 46
    last=df.iloc[-1]; prev=df.iloc[-2]
    total=last['High']-last['Low']; low_wick=min(last['Open'],last['Close'])-last['Low']
    ratio=low_wick/total if total>0 else 0
    bearish=sum(1 for i in range(len(df)-6, len(df)-1) if df.iloc[i]['Close'] < df.iloc[i]['Open'])
    bullish = last['Close']>last['Open'] and ratio>0.4
    rsi_ok = 30 <= last_rsi <= 58
    is_ruay = ratio>0.35 and rsi_ok and bullish and bearish>=2
    score=70 if is_ruay else 50
    if ratio>0.6: score+=15
    if rsi_ok: score+=10
    return dict(is_ruay=is_ruay, percent=min(88,int(score)), rsi=last_rsi, ratio=ratio)

def gen_chart(df, info, price):
    path=f"{CHART_DIR}/chart_5m.png"
    if os.path.exists(path): os.remove(path)
    fig,(ax1,ax2)=plt.subplots(2,1, figsize=(4,8.5), dpi=230, gridspec_kw={'height_ratios':[3.2,1]}, facecolor='black')
    dfp=df.tail(50).reset_index(drop=True)
    lmin=dfp['Low'].min(); hmax=dfp['High'].max(); rng=hmax-lmin or 3
    ax1.set_ylim(lmin-rng*0.18, hmax+rng*0.25); ax1.set_xlim(-1, len(dfp)+1)
    for idx,row in dfp.iterrows():
        o,h,l,c=row['Open'],row['High'],row['Low'],row['Close']
        col='#00E5FF' if c>=o else '#FF1493'
        ax1.plot([idx,idx],[l,h], color=col, lw=1.1)
        bh=abs(c-o) or rng*0.012
        ec='white' if info['is_ruay'] and idx>=len(dfp)-2 else col
        ax1.add_patch(plt.Rectangle((idx-0.3, min(o,c)), 0.6, bh, fc=col, ec=ec, lw=0.8 if ec=='white' else 0.5))
    if info['is_ruay']:
        sup=dfp['Low'].tail(10).min()
        ax1.axhline(sup, color='#00E5FF', lw=1)
        tp=sup+rng*0.5
        ax1.axhline(tp, color='#00E5FF', ls='--', lw=0.8, alpha=0.6)
    ax1.set_facecolor('black'); ax1.set_title(f"GOLD M5 RUAY {info['percent']}% Price {price:.2f} RSI {info['rsi']:.1f}", color='white', fontsize=9, fontweight='bold', loc='left')
    ax1.tick_params(colors='gray', labelsize=7); ax1.yaxis.tick_right()
    rsi=df['Close'].diff(); g=rsi.where(rsi>0,0).rolling(14).mean(); lo=-rsi.where(rsi<0,0).rolling(14).mean(); rsi_v=100-(100/(1+g/lo))
    ax2.plot(rsi_v.tail(50).values, color='#FF1493', lw=1.4); ax2.set_ylim(0,100); ax2.set_facecolor('black')
    ax2.text(1,5,f"RSI(14) {info['rsi']:.2f}", color='white', fontsize=8)
    plt.tight_layout(); plt.savefig(path, facecolor='black', dpi=230, bbox_inches='tight'); plt.close(fig)
    return path

def send_line(info, price):
    if not info['is_ruay']: return False
    img=f"{BASE_URL}/chart_5m.png?v={int(time.time())}"
    txt=f"[M5 RUAY สวยๆ] ไม้รวย {info['percent']}% Price {price:.2f} RSI {info['rsi']:.1f} ไส้ยาว {info['ratio']*100:.0f}% แบบในรูปพี่ BUY TP+5 USD {datetime.now().strftime('%H:%M:%S')}"
    r=requests.post("https://api.line.me/v2/bot/message/push", json={"to":LINE_USER_ID,"messages":[{"type":"image","originalContentUrl":img,"previewImageUrl":img},{"type":"text","text":txt}]}, headers={"Authorization": f"Bearer {LINE_TOKEN}"}, timeout=10)
    if r.status_code==200: mark_sent()
    return r.status_code==200

def loop():
    while True:
        try:
            df,price=fetch_m5(); info=detect_ruay(df); gen_chart(df,info,price)
            if info['is_ruay'] and info['percent']>=70 and can_send(): send_line(info,price)
            log(f"SCAN RUAY ONLY is={info['is_ruay']} {info['percent']}% RSI{info['rsi']:.1f}")
        except: pass
        time.sleep(60)
threading.Thread(target=loop, daemon=True).start()

@app.route('/')
def root(): return "M5 RUAY ONLY - Beautiful"
@app.route('/home')
def home():
    df,price=fetch_m5(); info=detect_ruay(df); info['is_ruay']=True; info['percent']=88
    gen_chart(df,info,price)
    return f"<body style='background:black;color:white;text-align:center'><h2 style='color:#00E5FF'>M5 RUAY ONLY สวยแบบนี้</h2><img src='/chart_5m.png?v={int(time.time())}' style='width:390px;border:2px solid #00E5FF'><br><br><a href='/test_line' style='background:#00E5FF;color:black;padding:10px 20px;border-radius:8px;text-decoration:none'>TEST ไม้รวยสวยๆ</a></body>"
@app.route('/chart_5m.png')
def c5(): return send_file(f"{CHART_DIR}/chart_5m.png", mimetype='image/png')
@app.route('/test_line')
def test():
    df,price=fetch_m5(); info=detect_ruay(df); info['is_ruay']=True; info['percent']=88; gen_chart(df,info,price); send_line(info,price)
    return f"TEST RUAY {info['percent']}%"
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
