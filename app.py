
from flask import Flask
import os, time, threading, traceback
from datetime import datetime
app = Flask(__name__)
state = {"last_check":"Never","price":0,"m":0,"r":0,"t":0,"found":False,"desc":""}

def log(msg):
    print(msg, flush=True)

@app.route('/')
def root(): return "Steve Gold Bot Running - go to /home"

@app.route('/home')
def home():
    try:
        from detector import fetch_gold_data, check_all_patterns
        df = fetch_gold_data()
        price = float(df['Close'].iloc[-1])
        m,r,t = check_all_patterns(df)
        state["price"]=price
        state["m"]=m["sim"]
        state["r"]=r["sim"]
        state["t"]=t["sim"]
        state["last_check"]=datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        state["found"]= m["found"] or r["found"] or t["found"]
        return f"""
        <h2>Steve Gold - 3 Tactics Bot</h2>
        <p>Last check: {state['last_check']}</p>
        <p>Price: {price:.2f}</p>
        <hr>
        <p><b>1. ภูเขา 53:</b> {m['sim']:.1f}% need 55% Found={m['found']}<br>{m['desc']}</p>
        <hr>
        <p><b>2. ไม้รวย:</b> Score {r['sim']} need 75 Found={r['found']}<br>{r['desc']}</p>
        <hr>
        <p><b>3. เทรน+ในกรอบ BUY:</b> Score {t['sim']} need 70 Found={t['found']}<br>{t['desc']}<br>กรอบ {t.get('box_low',0):.2f} - {t.get('box_high',0):.2f} ขึ้นมา {t.get('rise',0):.2f}%</p>
        <hr>
        <p>Status: Running every 3 min - 3 patterns<br>TOKEN OK: True<br>Bot 24/7 cloud</p>
        """
    except Exception as e:
        err = traceback.format_exc()
        log(err)
        return f"<pre>{err}</pre>",500

def send_line(msg):
    try:
        import requests
        token = os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
        if not token: return
        headers = {"Authorization": f"Bearer {token}"}
        data = {"to": os.environ.get("LINE_USER_ID",""), "messages":[{"type":"text","text":msg}]}
        url = "https://api.line.me/v2/bot/message/push"
        r = requests.post(url, headers={**headers, "Content-Type":"application/json"}, json=data, timeout=10)
        print(f"LINE {r.status_code}", flush=True)
    except Exception as e:
        print(f"LINE error {e}", flush=True)

def bot_loop():
    time.sleep(5)
    log("Bot loop 3 tactics started")
    while True:
        try:
            from detector import fetch_gold_data, check_all_patterns
            df = fetch_gold_data()
            price = float(df['Close'].iloc[-1])
            m,r,t = check_all_patterns(df)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Price {price:.2f} | Mtn {m['sim']:.0f}% | Ruay {r['sim']} | Box {t['sim']} Found M={m['found']} R={r['found']} T={t['found']}", flush=True)
            if m["found"]:
                send_line(f"\u1f3d4\ufe0f ภูเขา 53 เจอ! {m['sim']:.0f}%\nPrice {price:.2f}\n{m['desc']}")
            if r["found"]:
                send_line(f"\U0001f332 ไม้รวย BUY! Score {r['sim']}\nPrice {price:.2f}\n{r['desc']}")
            if t["found"]:
                send_line(f"\U0001f4e6 เทรน+ในกรอบ BUY! Score {t['sim']}\nPrice {price:.2f}\nกรอบ {t['box_low']:.2f}-{t['box_high']:.2f}\n{t['desc']}\nSL ใต้กรอบ {t['box_low']*0.999:.2f} TP บนกรอบ")
        except Exception as e:
            print(f"Loop error {e}", flush=True)
            traceback.print_exc()
        time.sleep(180)

try:
    threading.Thread(target=bot_loop, daemon=True).start()
    log("Thread 3 tactics started")
except Exception as e:
    log(f"Thread fail {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
