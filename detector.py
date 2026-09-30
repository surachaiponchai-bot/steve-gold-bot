
import requests, pandas as pd, numpy as np
from datetime import datetime

def fetch_gold_data(period='1d', interval='1m'):
    """ULTRA - Yahoo -> Coinbase -> mock"""
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
        df['Close'] = df['Close']*1.0
        df['Open'] = df['Open']*1.0
        df['High'] = df['High']*1.0
        df['Low'] = df['Low']*1.0
        return df.tail(300)

    for fn in [try_yahoo, try_coinbase]:
        try:
            df = fn()
            if len(df)>=30:
                print(f"{fn.__name__} OK: {len(df)} rows price {df['Close'].iloc[-1]:.2f}", flush=True)
                return df
        except Exception as e:
            print(f"{fn.__name__} fail: {e}", flush=True)
    # mock fallback
    print("Using MOCK data", flush=True)
    t = pd.date_range(end=datetime.now(), periods=100, freq='1min')
    price = 4180 + np.cumsum(np.random.randn(100)*0.5)
    df = pd.DataFrame({'Time':t,'Open':price,'High':price+1,'Low':price-1,'Close':price,'Volume':100})
    return df

def detect_mountain(df, need=53, threshold=55):
    """ท่า 1: ภูเขา 53 แท่ง"""
    if len(df) < need: 
        return {"found":False, "sim":0, "desc":f"data {len(df)}<{need}"}
    closes = df['Close'].values[-need:]
    # Simple similarity: normalized correlation with ideal mountain (low -> high -> low)
    ideal = np.concatenate([np.linspace(0,1,need//2), np.linspace(1,0,need-need//2)])
    c_norm = (closes - closes.min()) / (closes.max()-closes.min()+1e-9)
    sim = np.corrcoef(c_norm, ideal)[0,1]
    sim_pct = float(sim*100) if not np.isnan(sim) else 0
    # height
    low1 = closes[0]
    high = closes.max()
    low2 = closes[-1]
    height_pct = (high - min(low1,low2))/ min(low1,low2) *100
    found = sim_pct >= threshold and height_pct > 0.15
    desc = f"{need} แท่ง {low1:.2f} -> {high:.2f} -> {low2:.2f} สูง {height_pct:.3f}% เหมือน {sim_pct:.0f}%"
    return {"found":found, "sim":sim_pct, "desc":desc, "height":height_pct}

def detect_mai_ruay(df):
    """
    ท่า 2: ไม้รวย - Buy Reversal หลังโดนเท
    เงื่อนไขจากรูป:
    1. มีแท่งแดงใหญ่ลงแรง 5 แท่งล่าสุด ลง > 0.35% หรือแท่งแดงยาว > 1.8x avg
    2. แท่งปัจจุบันหรือก่อนหน้า 1 แท่ง มีไส้ล่างยาว > 60% ของแท่ง และต่ำกว่า Low 10 แท่งก่อนหน้า
    3. แท่งปัจจุบัน Bullish (Close > Open) หรือ Engulfing เขียว
    4. RSI < 50 (ถ้ามี)
    """
    if len(df) < 20:
        return {"found":False, "sim":0, "desc":"data น้อย"}
    last = df.iloc[-1]
    prev = df.iloc[-2]
    recent5 = df.iloc[-6:-1]  # 5 แท่งก่อนหน้า
    recent10 = df.iloc[-11:-1]

    # 1. ลงแรงไหม?
    drop_pct = (recent5['Close'].iloc[0] - recent5['Low'].min()) / recent5['Close'].iloc[0] * 100
    avg_range = (df['High']-df['Low']).tail(20).mean()
    big_red = (recent5['Open'] > recent5['Close']).sum() >= 3  # แดงเยอะ
    big_drop = drop_pct > 0.30 or (prev['High']-prev['Low']) > avg_range*1.8

    # 2. ไส้ล่างยาว?
    def is_pin(candle):
        body = abs(candle['Close']-candle['Open'])
        total = candle['High']-candle['Low']
        if total==0: return False
        lower_wick = min(candle['Open'], candle['Close']) - candle['Low']
        return lower_wick / total > 0.55 and total > avg_range*0.8

    pin_last = is_pin(last)
    pin_prev = is_pin(prev)
    # กวาด Low เดิม
    lowest_10 = recent10['Low'].min()
    sweep = last['Low'] < lowest_10 or prev['Low'] < lowest_10

    # 3. Bullish reversal?
    bullish = last['Close'] > last['Open'] and last['Close'] > prev['Open']*0.999
    # Engulfing: เขียวกลืนแดงก่อนหน้า
    engulfing = last['Close'] > last['Open'] and prev['Close'] < prev['Open'] and last['Close'] > prev['Open'] and last['Open'] < prev['Close']

    # 4. RSI ประมาณ (คำนวณง่ายๆ)
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

    desc = f"ไม้รวย: ลง {drop_pct:.2f}% แท่งแดงเยอะ ไส้ยาว {pin_last or pin_prev} กวาดLow {sweep} กลับตัวเขียว {bullish or engulfing} RSI {rsi:.1f} score {score}"

    return {"found":found, "sim":score, "desc":desc, "rsi":rsi, "pin":pin_last or pin_prev, "sweep":sweep}

def check_all_patterns(df):
    m = detect_mountain(df, need=53, threshold=55)
    r = detect_mai_ruay(df)
    return m, r
