
from flask import Flask, send_file
import os, time, threading, traceback
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io

app = Flask(__name__)
state = {"last_check":"Never","price":0,"m":0,"r":0,"t":0,"found":False,"desc":""}
CHART_PATH = "/tmp/latest_chart.png"
CHART_PATH2 = "/tmp/latest_chart2.png"

def log(msg):
    print(msg, flush=True)

def generate_chart(df, m=None, r=None, t=None, title="XAUUSD"):
    try:
        # ใช้ 60 แท่งล่าสุด
        plot_df = df.tail(60).copy()
        fig, ax = plt.subplots(figsize=(12,5), dpi=150)
        fig.patch.set_facecolor('black')
        ax.set_facecolor('black')
        
        # Plot candle as line + high low
        closes = plot_df['Close'].values
        highs = plot_df['High'].values
        lows = plot_df['Low'].values
        times = range(len(plot_df))
        
        # วาด high-low
        for i in range(len(plot_df)):
            ax.plot([i,i],[lows[i], highs[i]], color='#888888', linewidth=1, alpha=0.6)
            o = plot_df['Open'].values[i]
            c = closes[i]
            color = '#00ff88' if c >= o else '#ff4444'
            ax.plot([i-0.25, i+0.25],[o,o], color=color, linewidth=2)
            ax.plot([i-0.25, i+0.25],[c,c], color=color, linewidth=2)
        
        ax.plot(closes, color='#f5c518', linewidth=1.5, alpha=0.9)
        
        # วาดกรอบถ้ามี
        if t and 'box_low' in t:
            try:
                box_low = t['box_low']
                box_high = t['box_high']
                box_len = 12
                start_idx = len(plot_df) - box_len -1
                ax.fill_between([start_idx, len(plot_df)-1], box_low, box_high, color='cyan', alpha=0.15, label=f"Box {box_low:.1f}-{box_high:.1f}")
                ax.plot([start_idx, len(plot_df)-1],[box_low,box_low], color='cyan', linestyle='--', linewidth=1)
                ax.plot([start_idx, len(plot_df)-1],[box_high,box_high], color='cyan', linestyle='--', linewidth=1)
            except: pass
        
        # วาดภูเขา 53
        if m and m['sim'] > 30:
            try:
                ax.set_title(f"{title} {plot_df['Close'].iloc[-1]:.2f} | Mtn {m['sim']:.0f}% | Ruay {r['sim']} | Box {t['sim']} | {datetime.now().strftime('%H:%M:%S')}", color='white', fontsize=10)
            except:
                pass
        
        ax.grid(True, alpha=0.2, color='gray')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('#444444')
        
        plt.tight_layout()
        plt.savefig(CHART_PATH, facecolor='black', bbox_inches='tight')
        plt.savefig(CHART_PATH2, facecolor='black', bbox_inches='tight')
        plt.close()
        print(f"Chart saved {CHART_PATH}", flush=True)
        return CHART_PATH
    except Exception as e:
        print(f"Chart error {e}", flush=True)
        traceback.print_exc()
        return None

def send_line_text_image(text_msg, chart_url=None):
    try:
        import requests
        token = os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN") or os.environ.get("LINE_CHANNEL_TOKEN") or os.environ.get("LINE_ACCESS_TOKEN")
        user_id = os.environ.get("LINE_USER_ID") or os.environ.get("LINE_USER_ID_TO") or os.environ.get("USER_ID") or os.environ.get("LINE_TO")
        if not token: return "No LINE_TOKEN"
        if not user_id: return "No LINE_USER_ID"
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
        url = "https://api.line.me/v2/bot/message/push"
        
        messages = [{"type":"text","text":text_msg}]
        
        if chart_url:
            # ส่งภาพด้วย
            messages.append({
                "type":"image",
                "originalContentUrl": chart_url,
                "previewImageUrl": chart_url
            })
        
        data = {"to": user_id, "messages": messages}
        r = requests.post(url, headers=headers, json=data, timeout=15)
        print(f"LINE push {r.status_code} {r.text[:500]}", flush=True)
        return f"LINE {r.status_code}"
    except Exception as e:
        print(f"LINE error {e}", flush=True)
        return f"LINE error {e}"

def send_line(msg):
    return send_line_text_image(msg, None)

@app.route('/')
def root(): return "Steve Gold Bot Running Text+Image - go to /home or /test_line"

@app.route('/chart')
@app.route('/chart.png')
@app.route('/latest_chart.png')
def chart():
    try:
        if os.path.exists(CHART_PATH):
            return send_file(CHART_PATH, mimetype='image/png')
        else:
            return "No chart yet", 404
    except Exception as e:
        return str(e), 500

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
        
        # gen chart
        generate_chart(df, m, r, t, f"XAUUSD {price:.2f}")
        chart_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')}/chart.png?v={int(time.time())}"
        
        return f"""
        <h2>Steve Gold - OANDA:XAUUSD 5m Text+Image</h2>
        <p>Last check: {state['last_check']}</p>
        <p>OANDA:XAUUSD Price: {price:.2f}</p>
        <img src="/chart.png?v={int(time.time())}" style="width:100%;max-width:900px;border:1px solid #444">
        <hr>
        <p><b>1. ภูเขา 53:</b> {m['sim']:.1f}% need 55% Found={m['found']}<br>{m['desc']}</p>
        <hr>
        <p><b>2. ไม้รวย:</b> Score {r['sim']} need 75 Found={r['found']}<br>{r['desc']}</p>
        <hr>
        <p><b>3. เทรน+ในกรอบ BUY:</b> Score {t['sim']} need 70 Found={t['found']}<br>{t['desc']}<br>กรอบ {t.get('box_low',0):.2f} - {t.get('box_high',0):.2f} ขึ้นมา {t.get('rise',0):.2f}%</p>
        <hr>
        <p>Chart URL: {chart_url}</p>
        <p><a href="/test_line" style="background:green;color:white;padding:10px 20px;text-decoration:none;border-radius:5px">🔔 ทดสอบส่ง LINE ข้อความ+ภาพ</a></p>
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
        
        generate_chart(df, m, r, t, f"XAUUSD TEST {price:.2f}")
        # URL สำหรับ LINE ดึงภาพ
        base = os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
        chart_url = f"https://{base}/chart.png?v={int(time.time())}"
        
        results = []
        results.append(send_line_text_image(f"🔔 ทดสอบบอท Steve Gold 3 ท่า (Text+Image)\nOANDA:XAUUSD Price ตอนนี้ {price:.2f}\n\n1.ภูเขา 53: {m['sim']:.1f}%\n2.ไม้รวย: {r['sim']}\n3.เทรน+กรอบ: {t['sim']}\n\nบอททำงานปกติ 24/7 + ส่งภาพกราฟสด", chart_url))
        time.sleep(1)
        results.append(send_line_text_image(f"🏔️ ภูเขา 53 เจอ! {m['sim']:.0f}% (ตัวอย่าง)\nOANDA:XAUUSD Price {price:.2f}\n{m['desc']}\nSL ใต้ภูเขา TP ยอด", chart_url))
        time.sleep(1)
        results.append(send_line_text_image(f"🌲 ไม้รวย BUY! Score {r['sim']} (ตัวอย่าง)\nOANDA:XAUUSD Price {price:.2f}\n{r['desc']}", chart_url))
        time.sleep(1)
        results.append(send_line_text_image(f"📦 เทรน+ในกรอบ BUY! Score {t['sim']} (ตัวอย่าง)\nOANDA:XAUUSD Price {price:.2f}\nกรอบ {t.get('box_low',0):.2f}-{t.get('box_high',0):.2f}\n{t['desc']}", chart_url))
        
        return f"<h2>ส่ง LINE ทดสอบแล้ว 4 ชุด (ข้อความ+ภาพ)</h2><p>OANDA:XAUUSD Price {price:.2f}</p><p>Chart: {chart_url}</p><img src='/chart.png?v={int(time.time())}' style='width:100%;max-width:900px'><pre>{chr(10).join(results)}</pre><p><a href='/home'>กลับไป /home</a></p>"
    except Exception as e:
        err = traceback.format_exc()
        return f"<pre>{err}</pre>",500

def bot_loop():
    time.sleep(5)
    log("Bot loop OANDA 5m Text+Image started")
    while True:
        try:
            from detector import fetch_gold_data, check_all_patterns
            df = fetch_gold_data()
            price = float(df['Close'].iloc[-1])
            m,r,t = check_all_patterns(df)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] OANDA:XAUUSD Price {price:.2f} | Mtn {m['sim']:.0f}% | Ruay {r['sim']} | Box {t['sim']} Found M={m['found']} R={r['found']} T={t['found']}", flush=True)
            
            if m["found"] or r["found"] or t["found"]:
                chart_path = generate_chart(df, m, r, t, f"XAUUSD {price:.2f}")
                base = os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
                chart_url = f"https://{base}/chart.png?v={int(time.time())}"
                # รอ 2 วิให้ไฟล์พร้อม serve
                time.sleep(2)
            
            if m["found"]:
                base = os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
                chart_url = f"https://{base}/chart.png?v={int(time.time())}"
                send_line_text_image(f"🏔️ ภูเขา 53 เจอ! {m['sim']:.0f}%\nOANDA:XAUUSD Price {price:.2f}\n{m['desc']}", chart_url)
            if r["found"]:
                base = os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
                chart_url = f"https://{base}/chart.png?v={int(time.time())}"
                send_line_text_image(f"🌲 ไม้รวย BUY! Score {r['sim']}\nOANDA:XAUUSD Price {price:.2f}\n{r['desc']}", chart_url)
            if t["found"]:
                base = os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
                chart_url = f"https://{base}/chart.png?v={int(time.time())}"
                send_line_text_image(f"📦 เทรน+ในกรอบ BUY! Score {t['sim']}\nOANDA:XAUUSD Price {price:.2f}\nกรอบ {t['box_low']:.2f}-{t['box_high']:.2f}\n{t['desc']}", chart_url)
        except Exception as e:
            print(f"Loop error {e}", flush=True)
            traceback.print_exc()
        time.sleep(180)

try:
    threading.Thread(target=bot_loop, daemon=True).start()
    log("Thread OANDA 5m Text+Image started")
except Exception as e:
    log(f"Thread fail {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
