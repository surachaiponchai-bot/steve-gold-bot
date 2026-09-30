import os, time, threading
from datetime import datetime
from flask import Flask
import yfinance as yf

LINE_CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_TOKEN", "")
LINE_USER_ID = os.getenv("LINE_USER_ID", "")
CANDLE_COUNT = int(os.getenv("CANDLE_COUNT", "53"))
PATTERN_THRESHOLD = int(os.getenv("PATTERN_THRESHOLD", "55"))
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))

print(f"TOKEN set: {bool(LINE_CHANNEL_TOKEN)} len={len(LINE_CHANNEL_TOKEN)}")
print(f"Config: {CANDLE_COUNT} candles, need {PATTERN_THRESHOLD}%")

from detector import fetch_gold_data, generate_chart_image_53
from pattern_detector import check_53_mountain
from line_sender import send_line_text_and_image
import config

config.LINE_CHANNEL_TOKEN = LINE_CHANNEL_TOKEN
config.LINE_USER_ID = LINE_USER_ID

app = Flask(__name__)
last_result = {"time": "never", "similarity": 0, "status": "starting"}

def bot_loop():
    global last_result
    print("Bot loop started - checking every", CHECK_INTERVAL_MINUTES, "min")
    while True:
        try:
            df = fetch_gold_data(symbol="GC=F", period="2d", interval="5m")
            if len(df) < CANDLE_COUNT:
                print(f"Not enough data {len(df)}")
                time.sleep(60)
                continue
            df_53 = df.tail(CANDLE_COUNT).copy()
            current_price = float(df_53['Close'].iloc[-1])
            result = check_53_mountain(df_53)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 53c {df_53['Close'].iloc[0]:.2f}->{df_53['Close'].max():.2f}->{current_price:.2f} sim {result['similarity']:.0f}% corr {result.get('correlation',0):.0f}% peak@{result.get('peak_position',-1)} found={result['found']}")
            last_result = {
                "time": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                "price": current_price,
                "similarity": round(result['similarity'],1),
                "corr": round(result.get('correlation',0),1),
                "found": result['found'],
                "description": result['description']
            }
            if result['found'] and result['similarity'] >= PATTERN_THRESHOLD:
                chart_path = f"/tmp/chart_53_{datetime.now().strftime('%Y%m%d_%H%M')}.png"
                generate_chart_image_53(df_53, chart_path, result)
                msg = f"""\U0001f3d4\ufe0f Steve Gold - \u0e20\u0e39\u0e40\u0e02\u0e32 53 \u0e41\u0e17\u0e48\u0e07 \u0e1e\u0e1a! (Cloud)

\u0e04\u0e27\u0e32\u0e21\u0e40\u0e2b\u0e21\u0e37\u0e2d\u0e19: {result['similarity']:.0f}% (\u0e40\u0e1b\u0e49\u0e32 {PATTERN_THRESHOLD}%)
Price: ${current_price:.2f}
Time: {datetime.now().strftime('%d/%m/%Y %H:%M')}
\u0e20\u0e39\u0e40\u0e02\u0e32: {result['valley1']:.2f} -> {result['peak']:.2f} -> {result['valley2']:.2f}
\u0e2a\u0e39\u0e07: {result['height_pct']:.3f}%
Corr: {result.get('correlation',0):.0f}% peak@{result.get('peak_position',-1)}

Cloud bot \u0e15\u0e23\u0e27\u0e08 53 \u0e41\u0e17\u0e48\u0e07\u0e1b\u0e31\u0e08\u0e08\u0e38\u0e1a\u0e31\u0e19\u0e40\u0e1b\u0e47\u0e19\u0e20\u0e39\u0e40\u0e02\u0e32!

Signal: BUY/SELL \u0e15\u0e32\u0e21\u0e10\u0e32\u0e19"""
                print("SENDING ALERT to LINE...")
                send_line_text_and_image(msg, chart_path)
            time.sleep(CHECK_INTERVAL_MINUTES*60)
        except Exception as e:
            print(f"Loop error: {e}")
            import traceback; traceback.print_exc()
            time.sleep(60)

@app.route("/", methods=['GET', 'POST'])
@app.route("/callback", methods=['GET', 'POST'])
def callback():
    return 'OK', 200

@app.route("/home", methods=['GET', 'POST'])
def home():
    return f"""
    <h1>Steve Gold - 53 Candles Mountain Bot (Cloud)</h1>
    <p>Last check: {last_result['time']}</p>
    <p>Price: {last_result.get('price','-')}</p>
    <p>Similarity: {last_result.get('similarity',0)}% (need {PATTERN_THRESHOLD}%)</p>
    <p>Found: {last_result.get('found',False)}</p>
    <p>Desc: {last_result.get('description','')}</p>
    <p>Status: Running every {CHECK_INTERVAL_MINUTES} min, reading {CANDLE_COUNT} candles</p>
    <p>TOKEN OK: {bool(LINE_CHANNEL_TOKEN)}</p>
    <hr>
    <p>Bot is running 24/7 on cloud - no need to keep PC on!</p>
    """

@app.route("/test", methods=['GET', 'POST'])
def test_alert():
    try:
        msg = f"\U0001f9ea Test from Cloud Bot - {datetime.now().strftime('%H:%M:%S')} - Token OK: {bool(LINE_CHANNEL_TOKEN)} Price check OK"
        from line_sender import send_line_text
        send_line_text(msg)
        return f"Test sent! Token len {len(LINE_CHANNEL_TOKEN)}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
