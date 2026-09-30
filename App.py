from flask import Flask
import os, time, threading, traceback
from datetime import datetime

app = Flask(__name__)

# Global state
state = {
    "last_check": "Never",
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
