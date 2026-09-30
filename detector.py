
import requests, pandas as pd, numpy as np
from datetime import datetime

def fetch_gold_data(period='1d', interval='1m'):
    def try_yahoo():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range={period}&interval={interval}&includePrePost=false"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code!=200: raise Exception(f"Yahoo {r.status_code}")
        j = r.json()
        res = j['chart']['result'][0]
        ts = res['timestamp']
        q = res['indicators']['quote'][0]
        df = pd.DataFrame({
            'Time': pd.to_datetime(ts, unit='s'),
            'Open': q['open'],
            'High': q['high'],
            'Low': q['low'],
            'Close': q['close'],
            'Volume': q.get('volume',[0]*len(ts))
        }).dropna()
        return df
    def try_coinbase():
        url = "https://api.exchange.coinbase.com/products/XAU-USD/candles?granularity=60"
        r = requests.get(url, timeout=10)
        if r.status_code!=200: raise Exception(f"CB {r.status_code}")
        data = r.json()
        df = pd.DataFrame(data, columns=['Time','Low','High','Open','Close','Volume'])
        df['Time'] = pd.to_datetime(df['Time'], unit='s')
        df = df.sort_values('Time').reset_index(drop=True)
        return df.tail(300)
    for fn in [try_yahoo, try_coinbase]:
        try:
            df = fn()
            if len(df)>=30:
                print(f"{fn.__name__} OK: {len(df)} rows price {df['Close'].iloc[-1]:.2f}", flush=True)
                return df
        except Exception as e:
            print(f"{fn.__name__} fail: {e}", flush=True)
    print("Using MOCK data", flush=True)
    t = pd.date_range(end=datetime.now(), periods=100, freq='1min')
    price = 4180 + np.cumsum(np.random.randn(100)*0.5)
    df = pd.DataFrame({'Time':t,'Open':price,'High':price+1,'Low':price-1,'Close':price,'Volume':100})
    return df

def detect_mountain(df, need=53, threshold=55):
    if len(df) < need: 
        return {"found":False, "sim":0, "desc":f"data {len(df)}<{need}"}
    closes = df['Close'].values[-need:]
    ideal = np.concatenate([np.linspace(0,1,need//2), np.linspace(1,0,need-need//2)])
    c_norm = (closes - closes.min()) / (closes.max()-closes.min()+1e-9)
    sim = np.corrcoef(c_norm, ideal)[0,1]
    sim_pct = float(sim*100) if not np.isnan(sim) else 0
    low1 = closes[0]
    high = closes.max()
    low2 = closes[-1]
    height_pct = (high - min(low1,low2))/ min(low1,low2) *100
    found = sim_pct >= threshold and height_pct > 0.15
    desc = f"{need} แท่ง {low1:.2f} -> {high:.2f} -> {low2:.2f} สูง {height_pct:.3f}% เหมือน {sim_pct:.0f}%"
    return {"found":found, "sim":sim_pct, "desc":desc, "height":height_pct}

def detect_mai_ruay(df):
    if len(df) < 20:
        return {"found":False, "sim":0, "desc":"data น้อย"}
    last = df.iloc[-1]
    prev = df.iloc[-2]
    recent5 = df.iloc[-6:-1]
    recent10 = df.iloc[-11:-1]
    drop_pct = (recent5['Close'].iloc[0] - recent5['Low'].min()) / recent5['Close'].iloc[0] * 100
    avg_range = (df['High']-df['Low']).tail(20).mean()
    big_red = (recent5['Open'] > recent5['Close']).sum() >= 3
    big_drop = drop_pct > 0.30 or (prev['High']-prev['Low']) > avg_range*1.8
    def is_pin(candle):
        body = abs(candle['Close']-candle['Open'])
        total = candle['High']-candle['Low']
        if total==0: return False
        lower_wick = min(candle['Open'], candle['Close']) - candle['Low']
        return lower_wick / total > 0.55 and total > avg_range*0.8
    pin_last = is_pin(last)
    pin_prev = is_pin(prev)
    lowest_10 = recent10['Low'].min()
    sweep = last['Low'] < lowest_10 or prev['Low'] < lowest_10
    bullish = last['Close'] > last['Open'] and last['Close'] > prev['Open']*0.999
    engulfing = last['Close'] > last['Open'] and prev['Close'] < prev['Open'] and last['Close'] > prev['Open'] and last['Open'] < prev['Close']
    closes = df['Close'].values[-14:]
    gains = np.maximum(np.diff(closes),0).mean()
    losses = abs(np.minimum(np.diff(closes),0).mean())+1e-9
    rs = gains/losses
    rsi = 100 - (100/(1+rs))
    score = 0
    if big_drop: score+=30
    if big_red: score+=10
    if pin_last or pin_prev: score+=35
    if sweep: score+=15
    if bullish or engulfing: score+=20
    if rsi < 50: score+=10
    if rsi < 40: score+=5
    found = score >= 75 and (pin_last or pin_prev) and (bullish or engulfing) and sweep
    desc = f"ไม้รวย: ลง {drop_pct:.2f}% ไส้ยาว {pin_last or pin_prev} กวาดLow {sweep} กลับตัว {bullish or engulfing} RSI {rsi:.1f} score {score}"
    return {"found":found, "sim":score, "desc":desc, "rsi":rsi}

def detect_trend_in_box(df):
    """
    ท่า 3: เทรน+ในกรอบ BUY - จากรูปผู้ใช้
    M5 เป็นเทรนขึ้น + พักในกรอบแคบ + ลงมาแตะขอบล่างกรอบสดใหม่แล้ว Buy
    """
    if len(df) < 50:
        return {"found":False, "sim":0, "desc":"data น้อย <50"}

    # เตรียมข้อมูล
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values

    # 1. เทรนขึ้นไหม? M5 เทรนขึ้น = ดู 30 แท่งก่อนหน้า
    # ราคาปัจจุบันสูงกว่า EMA 20 และ 50, และขึ้นมา >1%
    def ema(arr, period):
        return pd.Series(arr).ewm(span=period, adjust=False).mean().values

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    price_now = closes[-1]
    up_trend = price_now > ema20[-1] and price_now > ema50[-1]
    # ขึ้นมาจากข้างล่างแรง
    rise_30 = (closes[-1] - closes[-30]) / closes[-30] * 100 if len(closes)>=30 else 0
    strong_up = rise_30 > 0.8  # ขึ้นมา >0.8% ใน 30 แท่ง

    # 2. หากรอบ: 10-15 แท่งล่าสุดเป็น Sideway แคบๆ (กล่อง)
    box_len = 12
    box = df.iloc[-box_len-1:-1]  # กรอบ ไม่รวมแท่งปัจจุบัน
    box_high = box['High'].max()
    box_low = box['Low'].min()
    box_range = box_high - box_low
    box_range_pct = box_range / box_low * 100
    avg_range = (df['High']-df['Low']).tail(30).mean()
    # กรอบต้องแคบ: range < 0.35% และ < 2.5 * avg_range
    is_box = box_range_pct < 0.45 and box_range < avg_range * 3.0 and box_range_pct > 0.05

    # 3. กรอบสดใหม่: ก่อนหน้ากรอบมีการพุ่งขึ้นแรง (แท่งเขียวใหญ่)
    before_box = df.iloc[-box_len-6:-box_len-1]
    if len(before_box) >=3:
        big_up_candle = (before_box['High'].max() - before_box['Low'].min()) > avg_range * 2.5
    else:
        big_up_candle = False

    # 4. แตะขอบล่างกรอบ
    last = df.iloc[-1]
    prev = df.iloc[-2]
    near_support = last['Low'] <= box_low * 1.0015 and last['Low'] >= box_low * 0.998
    touched_support = (last['Low'] <= box_low + box_range*0.15) or (prev['Low'] <= box_low + box_range*0.15)

    # 5. Reversal ที่ขอบล่าง: pin bar หรือ bullish engulfing ที่ขอบล่าง
    def is_bullish_pin(c):
        total = c['High']-c['Low']
        if total==0: return False
        lower_wick = min(c['Open'], c['Close']) - c['Low']
        return lower_wick / total > 0.4 and c['Close'] > c['Open']

    pin = is_bullish_pin(last) or is_bullish_pin(prev)
    bullish_close = last['Close'] > last['Open'] and last['Close'] > box_low

    # คะแนน
    score = 0
    if up_trend: score+=25
    if strong_up: score+=20
    if is_box: score+=25
    if big_up_candle: score+=10
    if touched_support: score+=15
    if near_support: score+=10
    if pin: score+=15
    if bullish_close: score+=10

    # เงื่อนไขเจอ
    found = up_trend and is_box and touched_support and bullish_close and score >= 70

    desc = f"เทรน+กรอบ: เทรนขึ้น {up_trend} ขึ้น {rise_30:.2f}% กรอบ {box_range_pct:.3f}% ({box_low:.2f}-{box_high:.2f}) สดใหม่ {big_up_candle} แตะรับล่าง {touched_support} pin {pin} score {score}"

    return {"found":found, "sim":score, "desc":desc, "box_low":box_low, "box_high":box_high, "rise":rise_30}

def check_all_patterns(df):
    m = detect_mountain(df, need=53, threshold=55)
    r = detect_mai_ruay(df)
    t = detect_trend_in_box(df)
    return m, r, t
