
import numpy as np, os, time, json
from datetime import datetime

COOLDOWN_FILE = "/tmp/last_send.json"
COOLDOWN_MIN = 15  # ส่งซ้ำได้ทุก 15 นาทีต่อ TF

def can_send(tf):
    try:
        if not os.path.exists(COOLDOWN_FILE): return True
        data=json.load(open(COOLDOWN_FILE))
        last=data.get(tf,0)
        return (time.time()-last) > COOLDOWN_MIN*60
    except: return True

def mark_sent(tf):
    try:
        data={}
        if os.path.exists(COOLDOWN_FILE):
            data=json.load(open(COOLDOWN_FILE))
        data[tf]=time.time()
        json.dump(data, open(COOLDOWN_FILE,'w'))
    except: pass

def detect_mountain(df, sim_thresh=55):
    try:
        closes=df['Close'].values
        if len(closes)<30: return {"sim":0,"perc":0,"start":0,"end":0,"found":False}
        recent=closes[-30:]
        # หา V shape จริงๆ ไม่ใช่ส่งมั่ว
        mid=np.argmin(recent)
        left=recent[:mid].max() if mid>5 else 0
        right=recent[mid+1:].max() if mid < len(recent)-5 else 0
        bottom=recent[mid]
        if left==0 or right==0: return {"sim":0,"perc":0,"start":0,"end":0,"found":False}
        up1=(left-bottom)/bottom*100
        up2=(right-bottom)/bottom*100
        # ต้องเป็นภูเขาจริงขึ้นมากกว่า 0.2%
        if up1<0.15 or up2<0.15: return {"sim":0,"perc":0,"start":left,"end":right,"found":False}
        sim = min(95, 60+ up1*10 + up2*10)
        return {"sim":int(sim),"perc":max(up1,up2),"start":left,"end":right,"found":sim>=60}
    except:
        return {"sim":0,"perc":0,"start":0,"end":0,"found":False}

def detect_ruay(df):
    try:
        # ต้องเป็นแท่งยาวจริง ไม่ใช่ส่งทุกอัน
        c=df['Close'].values[-5:]
        o=df['Open'].values[-5:] if 'Open' in df.columns else c
        big = 0
        for i in range(len(c)):
            body=abs(c[i]-o[i])/o[i]*100 if o[i]!=0 else 0
            if body>0.15: big+=1
        score = 50 if big>=2 else 0
        return {"sim":int(score)}
    except:
        return {"sim":0}

def detect_box(df):
    try:
        closes=df['Close'].values[-20:]
        high=closes.max(); low=closes.min()
        perc=(high-low)/low*100
        # กรอบต้องแคบมาก <0.15% ถึงจะน่าเทรด
        if perc>0.2: return {"sim":0,"box_low":low,"box_high":high,"perc":perc}
        sim=80 if perc<0.12 else 60
        return {"sim":sim,"box_low":low,"box_high":high,"perc":perc}
    except:
        return {"sim":0,"box_low":0,"box_high":0,"perc":0}

def detect_all(df):
    m=detect_mountain(df)
    r=detect_ruay(df)
    t=detect_box(df)
    return m,r,t
