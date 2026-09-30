import os, time, threading
from datetime import datetime
from flask import Flask

LINE_CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_TOKEN", "")
LINE_USER_ID = os.getenv("LINE_USER_ID", "")
CANDLE_COUNT = int(os.getenv("CANDLE_COUNT", "53"))
PATTERN_THRESHOLD = int(os.getenv("PATTERN_THRESHOLD", "55"))
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))

print(f"TOKEN OK: {bool(LINE_CHANNEL_TOKEN)}")
print(f"Config: {CANDLE_COUNT} candles, need {PATTERN_THRESHOLD}%")

from detector import fetch_gold_data, generate_chart_image_53
from pattern_detector import check_53_mountain
from line_sender import send_line_text_and_image
import config
config.LINE_CHANNEL_TOKEN = LINE_CHANNEL_TOKEN
config.LINE_USER_ID = LINE_USER_ID

app = Flask(__name__)
last_result = {"time": "never", "similarity": 0, "status": "starting", "price": "-"}

def bot_loop():
    global last_result
    print("Bot loop started - light mode")
    time.sleep(5)
    while True:
        try:
            df = fetch_gold_data()
            if len(df) < CANDLE_COUNT:
                print(f"Not enough data {len(df)}")
                time.sleep(60)
                continue
            df_53 = df.tail(CANDLE_COUNT).copy()
            current_price = float(df_53['Close'].iloc[-1])
            result = check_53_mountain(df_53)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Price {current_price:.2f} sim {result['similarity']:.0f}% found={result['found']}")
            last_result = {
                "time": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                "price": current_price,
                "similarity": round(result['similarity'],1),
                "found": result['found'],
                "description": result['description']
            }
            if result['found'] and result['similarity'] >= PATTERN_THRESHOLD:
                chart_path = f"/tmp/chart_53_{datetime.now().strftime('%Y%m%d_%H%M')}.png"
                generate_chart_image_53(df_53, chart_path, result)
                msg = f"🏔️ Steve Gold - ภูเขา 53 แท่ง พบ! (Cloud Light)\nความเหมือน: {result['similarity']:.0f}% (เป้า {PATTERN_THRESHOLD}%)\nPrice: ${current_price:.2f}\nTime: {datetime.now().strftime('%d/%m/%Y %H:%M')}\nภูเขา: {result['valley1']:.2f} -> {result['peak']:.2f} -> {result['valley2']:.2f}"
                print("SENDING ALERT")
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

@app.route("/home")
def home():
    return f"<h1>Steve Gold - 53 Candles Mountain Bot (Cloud Light)</h1><p>Last check: {last_result['time']}</p><p>Price: {last_result.get('price','-')}</p><p>Similarity: {last_result.get('similarity',0)}% (need {PATTERN_THRESHOLD}%)</p><p>Found: {last_result.get('found',False)}</p><p>Desc: {last_result.get('description','')}</p><p>Status: Running every {CHECK_INTERVAL_MINUTES} min, reading {CANDLE_COUNT} candles - LIGHT MODE 200MB</p><p>TOKEN OK: {bool(LINE_CHANNEL_TOKEN)}</p><hr>Bot is running 24/7 on cloud - no need to keep PC on!"

@app.route("/test")
def test_alert():
    try:
        from line_sender import send_line_text
        send_line_text(f"🧪 Test Light Bot {datetime.now().strftime('%H:%M:%S')}")
        return "Test sent light mode!"
    except Exception as e:
        return f"Error: {e}"

t = threading.Thread(target=bot_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
