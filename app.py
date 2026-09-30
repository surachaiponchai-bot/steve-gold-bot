
from flask import Flask, send_file
import os, time, threading, traceback
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

app = Flask(__name__)
state = {"last_check":"Never","price":0,"m":0,"r":0,"t":0,"found":False,"desc":""}
CHART_PATH = "/tmp/latest_chart.png"

def log(msg):
    print(msg, flush=True)

def generate_chart(df, m=None, r=None, t=None, title="XAUUSD"):
    try:
        plot_df = df.tail(60).copy().reset_index(drop=True)
        fig, ax = plt.subplots(figsize=(14,6), dpi=200)
        fig.patch.set_facecolor('#0a0a0a')
        ax.set_facecolor('#0a0a0a')
        
        # ===== แท่งเทียนสวยๆ แบบ MT4 =====
        for i in range(len(plot_df)):
            o = float(plot_df['Open'].iloc[i])
            h = float(plot_df['High'].iloc[i])
            l = float(plot_df['Low'].iloc[i])
            c = float(plot_df['Close'].iloc[i])
            
            is_bull = c >= o
            color = '#26a69a' if is_bull else '#ef5350'  # เขียว MT4 / แดง MT4
            wick_color = '#26a69a' if is_bull else '#ef5350'
            
            # ไส้เทียน (high-low)
            ax.plot([i, i], [l, h], color=wick_color, linewidth=1, alpha=0.9, zorder=1)
            
            # ตัวเทียน (body)
            body_bottom = min(o, c)
            body_top = max(o, c)
            body_height = abs(c - o)
            if body_height < (h-l)*0.05:  # Doji
                body_height = (h-l)*0.05
                body_bottom = (o+c)/2 - body_height/2
            
            rect = mpatches.Rectangle((i-0.3, body_bottom), 0.6, body_height if body_height>0 else 0.2,
                                      facecolor=color, edgecolor=color, linewidth=1, zorder=2, alpha=0.95)
            ax.add_patch(rect)
        
        # เส้นราคาปิดสีทองบางๆ
        closes = plot_df['Close'].values
        ax.plot(closes, color='#FFD700', linewidth=1, alpha=0.4, linestyle='-', zorder=0)
        
        # EMA 20/50
        try:
            import pandas as pd
            ema20 = pd.Series(closes).ewm(span=20).mean().values
            ema50 = pd.Series(closes).ewm(span=50).mean().values
            ax.plot(ema20, color='#2196F3', linewidth=1, alpha=0.7, label='EMA20')
            ax.plot(ema50, color='#FF9800', linewidth=1, alpha=0.7, label='EMA50')
        except:
            pass
        
        # วาดกรอบ เทรน+ในกรอบ
        if t and 'box_low' in t and t.get('sim',0) > 20:
            try:
                box_low = float(t['box_low'])
                box_high = float(t['box_high'])
                box_len = 12
                start_idx = len(plot_df) - box_len -1
                # กรอบ
                ax.fill_between([start_idx, len(plot_df)-1], box_low, box_high, color='#00e5ff', alpha=0.12, label=f"BOX {box_low:.1f}-{box_high:.1f}")
                ax.plot([start_idx, len(plot_df)-1],[box_low,box_low], color='#00e5ff', linestyle='--', linewidth=1.5, alpha=0.9)
                ax.plot([start_idx, len(plot_df)-1],[box_high,box_high], color='#00e5ff', linestyle='--', linewidth=1.5, alpha=0.9)
                # ลูกศรชี้
                ax.annotate('BUY Zone', xy=(len(plot_df)-1, box_low), xytext=(len(plot_df)-8, box_low- (box_high-box_low)*1.2),
                            color='#00e5ff', fontsize=9, fontweight='bold',
                            arrowprops=dict(facecolor='#00e5ff', shrink=0.05, width=1))
            except Exception as e:
                print(f"box draw err {e}")
        
        # ตกแต่ง
        ax.set_title(f"{title} | OANDA:XAUUSD 5m | Price {plot_df['Close'].iloc[-1]:.2f} | Mtn {m['sim']:.0f}% | Ruay {r['sim']} | Box {t['sim']} | {datetime.now().strftime('%H:%M:%S')}", 
                     color='white', fontsize=11, fontweight='bold', loc='left')
        
        ax.grid(True, alpha=0.15, color='gray', linestyle='--')
        ax.tick_params(colors='white', labelsize=8)
        for spine in ax.spines.values():
            spine.set_color('#333333')
        
        # legend
        legend = ax.legend(facecolor='#1a1a1a', edgecolor='#444444', fontsize=8, loc='upper left')
        for text in legend.get_texts():
            text.set_color('white')
        
        ax.set_xlim(-1, len(plot_df))
        # y limit ให้สวย
        low = plot_df['Low'].min()
        high = plot_df['High'].max()
        pad = (high-low)*0.15
        ax.set_ylim(low-pad, high+pad)
        
        plt.tight_layout()
        plt.savefig(CHART_PATH, facecolor='#0a0a0a', bbox_inches='tight')
        plt.close()
        print(f"Chart CANDLE saved {CHART_PATH}", flush=True)
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
            messages.append({"type":"image","originalContentUrl": chart_url,"previewImageUrl": chart_url})
        data = {"to": user_id, "messages": messages}
        r = requests.post(url, headers=headers, json=data, timeout=15)
        print(f"LINE push {r.status_code} {r.text[:500]}", flush=True)
        return f"LINE {r.status_code}"
    except Exception as e:
        print(f"LINE error {e}", flush=True)
        return f"LINE error {e}"

@app.route('/')
def root(): return "Steve Gold CANDLE - go to /home or /test_line"

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
        generate_chart(df, m, r, t, f"XAUUSD {price:.2f}")
        return f"""
        <h2 style="font-family:sans-serif">Steve Gold - OANDA:XAUUSD 5m CANDLESTICK</h2>
        <p>Last check: {state['last_check']} | Price: {price:.2f} | CANDLESTICK MT4 Style</p>
        <img src="/chart.png?v={int(time.time())}" style="width:100%;max-width:1100px;border:1px solid #444;border-radius:8px">
        <hr>
        <p><b>1. ภูเขา 53:</b> {m['sim']:.1f}% need 55% Found={m['found']}<br>{m['desc']}</p>
        <p><b>2. ไม้รวย:</b> Score {r['sim']} need 75 Found={r['found']}<br>{r['desc']}</p>
        <p><b>3. เทรน+ในกรอบ BUY:</b> Score {t['sim']} need 70 Found={t['found']}<br>{t['desc']}<br>กรอบ {t.get('box_low',0):.2f} - {t.get('box_high',0):.2f}</p>
        <hr>
        <p><a href="/test_line" style="background:#26a69a;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:bold">🔔 ทดสอบส่ง LINE ข้อความ+แท่งเทียน</a></p>
        """
    except Exception as e:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>",500

@app.route('/test_line')
def test_line():
    try:
        from detector import fetch_gold_data, check_all_patterns
        df = fetch_gold_data()
        price = float(df['Close'].iloc[-1])
        m,r,t = check_all_patterns(df)
        generate_chart(df, m, r, t, f"XAUUSD TEST CANDLE {price:.2f}")
        base = os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
        chart_url = f"https://{base}/chart.png?v={int(time.time())}"
        results = []
        time.sleep(1)
        results.append(send_line_text_image(f"🔔 ทดสอบ CANDLESTICK MT4\nOANDA:XAUUSD Price {price:.2f}\nแท่งเทียนเขียว/แดง + EMA20/50 + กรอบ BUY\nMtn {m['sim']:.0f}% Ruay {r['sim']} Box {t['sim']}", chart_url))
        time.sleep(1)
        results.append(send_line_text_image(f"🏔️ ภูเขา 53 {m['sim']:.0f}% [CANDLE]\nPrice {price:.2f}\n{m['desc']}", chart_url))
        time.sleep(1)
        results.append(send_line_text_image(f"🌲 ไม้รวย BUY Score {r['sim']} [CANDLE]\nPrice {price:.2f}\n{r['desc']}", chart_url))
        time.sleep(1)
        results.append(send_line_text_image(f"📦 เทรน+ในกรอบ BUY Score {t['sim']} [CANDLE]\nPrice {price:.2f}\nกรอบ {t.get('box_low',0):.2f}-{t.get('box_high',0):.2f}\n{t['desc']}", chart_url))
        return f"<h2>ส่ง LINE CANDLESTICK แล้ว 4 ชุด</h2><img src='/chart.png?v={int(time.time())}' style='width:100%;max-width:1100px'><pre>{chr(10).join(results)}</pre>"
    except Exception as e:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>",500

def bot_loop():
    time.sleep(5)
    log("Bot loop OANDA CANDLESTICK started")
    while True:
        try:
            from detector import fetch_gold_data, check_all_patterns
            df = fetch_gold_data()
            price = float(df['Close'].iloc[-1])
            m,r,t = check_all_patterns(df)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] CANDLE Price {price:.2f} M{m['sim']:.0f}% R{r['sim']} T{t['sim']} Found {m['found']}/{r['found']}/{t['found']}", flush=True)
            if m["found"] or r["found"] or t["found"]:
                generate_chart(df, m, r, t, f"XAUUSD {price:.2f}")
                time.sleep(2)
                base = os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
                chart_url = f"https://{base}/chart.png?v={int(time.time())}"
                if m["found"]: send_line_text_image(f"🏔️ ภูเขา 53 {m['sim']:.0f}%\nOANDA:XAUUSD Price {price:.2f}\n{m['desc']}", chart_url)
                if r["found"]: send_line_text_image(f"🌲 ไม้รวย BUY Score {r['sim']}\nOANDA:XAUUSD Price {price:.2f}\n{r['desc']}", chart_url)
                if t["found"]: send_line_text_image(f"📦 เทรน+ในกรอบ BUY Score {t['sim']}\nOANDA:XAUUSD Price {price:.2f}\nกรอบ {t.get('box_low',0):.2f}-{t.get('box_high',0):.2f}\n{t['desc']}", chart_url)
        except Exception as e:
            print(f"Loop err {e}")
        time.sleep(180)

try:
    threading.Thread(target=bot_loop, daemon=True).start()
except: pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
