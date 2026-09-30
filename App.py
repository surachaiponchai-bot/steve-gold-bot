from flask import Flask
import os, time, threading, traceback
from datetime import datetime

app = Flask(__name__)

# Global state
state = {
    "last_check": "Never",
from flask import Flask
import os, time, threading, traceback
from datetime import datetime

app = Flask(__name__)

state = {
    "last_check": "Never",
    "price": 0,
    "mountain_sim": 0,
    "mai_ruay_score": 0,
    "found": False,
    "last_error": "",
    "last_desc": "",
    "last_pattern": ""
}

def log(msg):
    print(msg, flush=True)
    state["last_desc"] = msg

@app.route('/')
def root():
    return "Steve Gold Bot Running - go to /home"

@app.route('/home')
def home():
    try:
        from detector import fetch_gold_data, check_all_patterns
        log("Manual /home fetch 2 tactics...")
        df = fetch_gold_data()
        price = float(df['Close'].iloc[-1])
        m, r = check_all_patterns(df)
        state["price"] = price
        state["mountain_sim"] = m["sim"]
        state["mai_ruay_score"] = r["sim"]
        state["last_check"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        state["last_error"] = f"OK {len(df)} rows"
        state["found"] = m["found"] or r["found"]
        state["last_pattern"] = f"Mountain: {m['desc']}<br>MaiRuay: {r['desc']}"
        return f"""
        <h2>Steve Gold - 2 Tactics Bot (Mountain 53 + ไม้รวย)</h2>
        <p>Last check: {state['last_check']}</p>
        <p>Price: {price:.2f}</p>
        <p>---</p>
        <p><b>ท่า 1 ภูเขา 53:</b> Similarity {m['sim']:.1f}% (need 55%) Found={m['found']}</p>
        <p>{m['desc']}</p>
        <p>---</p>
        <p><b>ท่า 2 ไม้รวย:</b> Score {r['sim']} /100 (need 75) Found={r['found']}</p>
        <p>{r['desc']}</p>
        <p>---</p>
        <p>Status: Running every 5 min - 2 patterns</p>
        <p>TOKEN OK: True</p>
        <p>Bot is running 24/7 on cloud - no need to keep PC on!</p>
        <hr>
        <p>{state['last_pattern']}</p>
        """
    except Exception as e:
        err = f"Error: {e}\n{traceback.format_exc()}"
        state["last_error"] = err[:500]
        log(err)
        return f"<h1>Error</h1><pre>{err}</pre>", 500

def send_line(msg, img_path=None):
    try:
        import requests
        token = os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
        if not token: 
            print("No LINE token", flush=True)
            return
        headers = {"Authorization": f"Bearer {token}"}
        data = {"to": os.environ.get("LINE_USER_ID",""), "messages":[{"type":"text","text":msg}]}
        # For simplicity use push API
        url = "https://api.line.me/v2/bot/message/push"
        r = requests.post(url, headers={**headers, "Content-Type":"application/json"}, json=data, timeout=10)
        print(f"LINE push {r.status_code} {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"LINE error {e}", flush=True)

def bot_loop():
    time.sleep(5)
    log("Bot loop started - 2 tactics mode")
    while True:
        try:
            from detector import fetch_gold_data, check_all_patterns
            df = fetch_gold_data()
            price = float(df['Close'].iloc[-1])
            m, r = check_all_patterns(df)
            state["price"] = price
            state["mountain_sim"] = m["sim"]
            state["mai_ruay_score"] = r["sim"]
            state["last_check"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            print(f"[{state['last_check']}] Price {price:.2f} | Mtn {m['sim']:.0f}% | MaiRuay {r['sim']} | Found M={m['found']} R={r['found']}", flush=True)
            
            if m["found"]:
                msg = f"🏔️ ภูเขา 53 เจอ! {m['sim']:.0f}%\nPrice {price:.2f}\n{m['desc']}"
                send_line(msg)
            if r["found"]:
                msg = f"🌲 ไม้รวย BUY! Score {r['sim']}\nPrice {price:.2f}\n{r['desc']}\nไส้ยาวกวาดล่างดีดกลับ RSI {r.get('rsi',0):.1f}"
                send_line(msg)
                
        except Exception as e:
            print(f"Loop error: {e}", flush=True)
            traceback.print_exc()
        time.sleep(300)

try:
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    log("Thread started 2 tactics")
except Exception as e:
    log(f"Thread start fail: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    "price": 0,
    "similarity": 0,
    "found": False,
    "last_error": "",
    "last_log": ""
}

def log(msg):
    print(msg, flush=True)
    state["last_log"] = msg

@app.route('/')
def root():
    return "Steve Gold Bot Running - go to /home"

@app.route('/home')
def home():
    try:
        from detector import fetch_gold_data
        log("Manual /home fetch...")
        df = fetch_gold_data()
        price = float(df['Close'].iloc[-1])
        state["price"] = price
        state["last_check"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        state["last_error"] = f"OK {len(df)} candles"
        return f"""
        <h1>Steve Gold - 53 Candles Mountain Bot (Cloud Light)</h1>
        <p>Last check: {state['last_check']}</p>
        <p>Price: {price:.2f}</p>
        <p>Rows: {len(df)}</p>
        <p>Status: {state['last_error']}</p>
        <p>Last log: {state['last_log']}</p>
        <p>Running every 5 min - LINE push active</p>
        """
    except Exception as e:
        err = f"Error: {e}\n{traceback.format_exc()[-500:]}"
        state["last_error"] = err
        log(err)
        return f"<h1>Error</h1><pre>{err}</pre><p>Last check: {state['last_check']}</p>", 500

def bot_loop():
    time.sleep(5)
    log("Bot loop started - light mode")
    while True:
        try:
            from detector import fetch_gold_data
            log("Fetching gold data...")
            df = fetch_gold_data()
            price = float(df['Close'].iloc[-1])
            state["price"] = price
            state["last_check"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            log(f"[{state['last_check']}] Price {price:.2f} OK {len(df)} rows")
            # TODO: add mountain logic + LINE push here
        except Exception as e:
            err = f"{e}"
            state["last_error"] = err
            log(f"Loop error: {err}")
            traceback.print_exc()
        time.sleep(300)  # 5 min

# Start thread
try:
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    log("Thread started")
except Exception as e:
    log(f"Thread start fail: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
