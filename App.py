
from flask import Flask
import os, time, threading, traceback
from datetime import datetime
app = Flask(__name__)
state = {"last_check":"Never","price":0,"m":0,"r":0,"t":0,"found":False,"desc":""}

def log(msg):
    print(msg, flush=True)

def send_line(msg):
    try:
        import requests
        token = os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
        user_id = os.environ.get("LINE_USER_ID") or os.environ.get("LINE_USER_ID_TO") or os.environ.get("USER_ID")
        print(f"LINE config token exists={bool(token)} user_id exists={bool(user_id)}", flush=True)
        if not token: 
            return "No LINE_TOKEN"
        if not user_id:
            return "No LINE_USER_ID"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"to": user_id, "messages":[{"type":"text","text":msg}]}
        url = "https://api.line.me/v2/bot/message/push"
        r = requests.post(url, headers={**headers, "Content-Type":"application/json"}, json=data, timeout=10)
        print(f"LINE push {r.status_code} {r.text[:500]}", flush=True)
        return f"LINE {r.status_code} {r.text[:500]}"
    except Exception as e:
        print(f"LINE error {e}", flush=True)
        return f"LINE error {e}"

@app.route('/')
def root(): return "Steve Gold Bot Running - go to /home or /test_line"

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
        <hr>
        <p><a href="/test_line" style="background:green;color:white;padding:10px 20px;text-decoration:none;border-radius:5px">🔔 ทดสอบส่ง LINE 3 ท่า</a></p>
        """
    except Exception as e:
        err = traceback.format_exc()
        log(err)
        return f"<pre>{err}</pre>",500

@app.route('/test_line')
def test_line():
    try:
        from detector import fetch_gold_data, check_all_patterns
        df = fetch_gold_data()
        price = float(df['Close'].iloc[-1])
        m,r,t = check_all_patterns(df)
        results = []
        results.append(send_line(f"🔔 ทดสอบบอท Steve Gold 3 ท่า\nPrice ตอนนี้ {price:.2f}\n\n1.ภูเขา 53: {m['sim']:.1f}%\n2.ไม้รวย: {r['sim']}\n3.เทรน+กรอบ: {t['sim']}\n\nบอททำงานปกติ 24/7"))
        results.append(send_line(f"🏔️ ภูเขา 53 เจอ! {m['sim']:.0f}% (ตัวอย่าง)\nPrice {price:.2f}\n{m['desc']}\nSL ใต้ภูเขา TP ยอด"))
        results.append(send_line(f"🌲 ไม้รวย BUY! Score {r['sim']} (ตัวอย่าง)\nPrice {price:.2f}\n{r['desc']}\nไส้ยาวกวาดล่างดีดกลับ RSI ต่ำ"))
        results.append(send_line(f"📦 เทรน+ในกรอบ BUY! Score {t['sim']} (ตัวอย่าง)\nPrice {price:.2f}\nกรอบ {t.get('box_low',0):.2f}-{t.get('box_high',0):.2f}\nSL ใต้กรอบ {t.get('box_low',0)*0.999:.2f} TP บนกรอบ\n{t['desc']}"))
        return f"<h2>ส่ง LINE ทดสอบแล้ว 4 ข้อความ</h2><p>Price {price:.2f}</p><pre>{chr(10).join(results)}</pre><p><a href='/home'>กลับไป /home</a></p>"
    except Exception as e:
        err = traceback.format_exc()
        return f"<pre>{err}</pre>",500

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
                send_line(f"🏔️ ภูเขา 53 เจอ! {m['sim']:.0f}%\nPrice {price:.2f}\n{m['desc']}")
            if r["found"]:
                send_line(f"🌲 ไม้รวย BUY! Score {r['sim']}\nPrice {price:.2f}\n{r['desc']}")
            if t["found"]:
                send_line(f"📦 เทรน+ในกรอบ BUY! Score {t['sim']}\nPrice {price:.2f}\nกรอบ {t['box_low']:.2f}-{t['box_high']:.2f}\n{t['desc']}")
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
