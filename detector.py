
import numpy as np, os, time, json

COOLDOWN_FILE = "/tmp/last_send_m5.json"
COOLDOWN_MIN = 15

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
            try: data=json.load(open(COOLDOWN_FILE))
            except: pass
        data[tf]=time.time()
        json.dump(data, open(COOLDOWN_FILE,'w'))
    except: pass

def detect_mountain(df):
    """ท่าที่ 1: ภูเขา - V Shape เด้งขึ้น"""
    try:
        closes=df['Close'].values
        if len(closes)<30: return {"name":"ภูเขา","sim":0,"perc":0,"found":False}
        recent=closes[-25:]
        mid=np.argmin(recent)
        if mid<5 or mid>20: return {"name":"ภูเขา","sim":0,"perc":0,"found":False}
        left_max=recent[:mid].max()
        right_max=recent[mid+1:].max()
        bottom=recent[mid]
        up_left=(left_max-bottom)/bottom*100
        up_right=(right_max-bottom)/bottom*100
        if up_left<0.12 or up_right<0.12: return {"name":"ภูเขา","sim":0,"perc":max(up_left,up_right),"found":False}
        sim = min(95, 65 + (up_left+up_right)*30)
        return {"name":"ภูเขา","sim":int(sim),"perc":max(up_left,up_right),"start":left_max,"end":right_max,"found":sim>=65}
    except Exception as e:
        return {"name":"ภูเขา","sim":0,"perc":0,"found":False}

def detect_ruay(df):
    """ท่าที่ 2: ไม้รวย - แท่งใหญ่ต่อเนื่อง"""
    try:
        closes=df['Close'].values[-6:]
        opens=df['Open'].values[-6:] if 'Open' in df.columns else closes
        big_count=0
        total_body=0
        for i in range(len(closes)):
            body=abs(closes[i]-opens[i])/opens[i]*100 if opens[i]!=0 else 0
            total_body+=body
            if body>0.18: big_count+=1
        if big_count<2: return {"name":"ไม้รวย","sim":0,"perc":total_body,"found":False}
        sim = 75 + big_count*10 + total_body*20
        return {"name":"ไม้รวย","sim":int(min(95,sim)),"perc":total_body,"found":sim>=80}
    except:
        return {"name":"ไม้รวย","sim":0,"perc":0,"found":False}

def detect_box(df):
    """ท่าที่ 3: กรอบแตก - Sideway แคบแล้วเบรก"""
    try:
        closes=df['Close'].values[-20:]
        high=closes.max(); low=closes.min()
        perc=(high-low)/low*100
        if perc>0.18: return {"name":"กรอบแตก","sim":0,"perc":perc,"box_low":low,"box_high":high,"found":False}
        # ถ้าแคบมากแล้วแท่งสุดท้ายเบรกแรง
        last=closes[-1]
        prev_avg=np.mean(closes[-6:-1])
        break_strength=abs(last-prev_avg)/prev_avg*100
        sim = 70 if perc<0.14 else 50
        if break_strength>0.08: sim+=15
        return {"name":"กรอบแตก","sim":int(min(95,sim)),"perc":perc,"box_low":low,"box_high":high,"found":sim>=75}
    except:
        return {"name":"กรอบแตก","sim":0,"perc":0,"box_low":0,"box_high":0,"found":False}

def detect_all(df):
    m=detect_mountain(df)
    r=detect_ruay(df)
    t=detect_box(df)
    return m,r,t
