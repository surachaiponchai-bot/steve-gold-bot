
from flask import Flask, send_file
import os, time, threading, traceback
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

app = Flask(__name__)
CHART_DIR = "/tmp"
TIMEFRAMES = ["1m", "5m", "15m", "30m"]

def log(msg): print(msg, flush=True)

def generate_chart_tf(df, m, r, t, tf_label, price):
    try:
        from detector import fetch_gold_data
        plot_df = df.tail(60).copy().reset_index(drop=True)
        path = f"{CHART_DIR}/chart_{tf_label}.png"
        fig, ax = plt.subplots(figsize=(14,6), dpi=200)
        fig.patch.set_facecolor('#0a0a0a')
        ax.set_facecolor('#0a0a0a')
        for i in range(len(plot_df)):
            o=float(plot_df['Open'].iloc[i]); h=float(plot_df['High'].iloc[i]); l=float(plot_df['Low'].iloc[i]); c=float(plot_df['Close'].iloc[i])
            is_bull=c>=o; color='#26a69a' if is_bull else '#ef5350'
            ax.plot([i,i],[l,h], color=color, linewidth=1, alpha=0.9, zorder=1)
            body_bottom=min(o,c); body_height=abs(c-o)
            if body_height < (h-l)*0.05:
                body_height=(h-l)*0.05; body_bottom=(o+c)/2-body_height/2
            rect=mpatches.Rectangle((i-0.3, body_bottom),0.6, body_height if body_height>0 else 0.2, facecolor=color, edgecolor=color, linewidth=1, zorder=2, alpha=0.95)
            ax.add_patch(rect)
        closes=plot_df['Close'].values
        ax.plot(closes, color='#FFD700', linewidth=1, alpha=0.4, zorder=0)
        try:
            import pandas as pd
            ema20=pd.Series(closes).ewm(span=20).mean().values
            ema50=pd.Series(closes).ewm(span=50).mean().values
            ax.plot(ema20, color='#2196F3', linewidth=1, alpha=0.7, label='EMA20')
            ax.plot(ema50, color='#FF9800', linewidth=1, alpha=0.7, label='EMA50')
        except: pass
        if t and 'box_low' in t and t.get('sim',0)>20:
            try:
                box_low=float(t['box_low']); box_high=float(t['box_high']); box_len=12; start_idx=len(plot_df)-box_len-1
                ax.fill_between([start_idx, len(plot_df)-1], box_low, box_high, color='#00e5ff', alpha=0.12, label=f"BOX {box_low:.1f}-{box_high:.1f}")
                ax.plot([start_idx, len(plot_df)-1],[box_low,box_low], color='#00e5ff', linestyle='--', linewidth=1.5, alpha=0.9)
                ax.plot([start_idx, len(plot_df)-1],[box_high,box_high], color='#00e5ff', linestyle='--', linewidth=1.5, alpha=0.9)
            except: pass
        ax.set_title(f"{tf_label} | OANDA:XAUUSD {tf_label} | Price {price:.2f} | Mtn {m['sim']:.0f}% | Ruay {r['sim']} | Box {t['sim']} | {datetime.now().strftime('%H:%M:%S')}", color='white', fontsize=11, fontweight='bold', loc='left')
        ax.grid(True, alpha=0.15, color='gray', linestyle='--')
        ax.tick_params(colors='white', labelsize=8)
        for spine in ax.spines.values(): spine.set_color('#333333')
        legend=ax.legend(facecolor='#1a1a1a', edgecolor='#444444', fontsize=8, loc='upper left')
        for text in legend.get_texts(): text.set_color('white')
        ax.set_xlim(-1, len(plot_df))
        low=plot_df['Low'].min(); high=plot_df['High'].max(); pad=(high-low)*0.15
        ax.set_ylim(low-pad, high+pad)
        plt.tight_layout()
        plt.savefig(path, facecolor='#0a0a0a', bbox_inches='tight')
        plt.close()
        log(f"Chart {tf_label} saved {path}")
        return path
    except Exception as e:
        log(f"Chart {tf_label} error {e}")
        traceback.print_exc()
        return None

def send_line_text_image(text_msg, chart_url=None):
    try:
        import requests
        token=os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN") or os.environ.get("LINE_ACCESS_TOKEN")
        user_id=os.environ.get("LINE_USER_ID") or os.environ.get("LINE_USER_ID_TO")
        if not token or not user_id: return "No token/user"
        headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
        url="https://api.line.me/v2/bot/message/push"
        messages=[{"type":"text","text":text_msg}]
        if chart_url:
            messages.append({"type":"image","originalContentUrl": chart_url,"previewImageUrl": chart_url})
        data={"to": user_id, "messages": messages}
        r=requests.post(url, headers=headers, json=data, timeout=15)
        log(f"LINE {tf_label if 'tf_label' in locals() else ''} {r.status_code}")
        return f"LINE {r.status_code}"
    except Exception as e:
        log(f"LINE err {e}")
        return str(e)

def send_line_multi(text, tf_label):
    try:
        import requests
        token=os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"); user_id=os.environ.get("LINE_USER_ID") or os.environ.get("USER_ID")
        if not token or not user_id: return
        headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
        base=os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
        chart_url=f"https://{base}/chart_{tf_label}.png?v={int(time.time())}"
        url="https://api.line.me/v2/bot/message/push"
        messages=[{"type":"text","text":text},{"type":"image","originalContentUrl": chart_url,"previewImageUrl": chart_url}]
        data={"to": user_id, "messages": messages}
        r=requests.post(url, headers=headers, json=data, timeout=15)
        log(f"PUSH {tf_label} {r.status_code}")
    except Exception as e:
        log(f"send multi err {e}")

@app.route('/')
def root(): return "Multi TF Bot M1 M5 M15 M30 - /home"

@app.route('/home')
def home():
    try:
        from detector import fetch_gold_data_tf, check_all_patterns
        html="<h2>Steve Gold - Multi TF M1 M5 M15 M30 CANDLESTICK</h2>"
        for tf in TIMEFRAMES:
            df=fetch_gold_data_tf(interval=tf)
            price=float(df['Close'].iloc[-1])
            m,r,t=check_all_patterns(df)
            generate_chart_tf(df,m,r,t,tf,price)
            html+=f"<h3>{tf} Price {price:.2f} Mtn {m['sim']:.0f}% R {r['sim']} T {t['sim']} Found {m['found']}/{r['found']}/{t['found']}</h3>"
            html+=f"<img src='/chart_{tf}.png?v={int(time.time())}' style='width:100%;max-width:1100px;border:1px solid #444'><hr>"
        html+=f"<p><a href='/test_line' style='background:green;color:white;padding:10px 20px;text-decoration:none'>ทดสอบส่ง LINE Multi TF</a></p>"
        return html
    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>",500

@app.route('/chart_<tf>.png')
def chart_tf(tf):
    try:
        p=f"{CHART_DIR}/chart_{tf}.png"
        if os.path.exists(p): return send_file(p, mimetype='image/png')
        return "No chart",404
    except Exception as e: return str(e),500

@app.route('/chart.png')
def chart_default():
    return chart_tf('5m')

@app.route('/test_line')
def test_line():
    try:
        from detector import fetch_gold_data_tf, check_all_patterns
        res=[]
        for tf in TIMEFRAMES:
            df=fetch_gold_data_tf(interval=tf)
            price=float(df['Close'].iloc[-1])
            m,r,t=check_all_patterns(df)
            generate_chart_tf(df,m,r,t,tf,price)
            time.sleep(1)
            base=os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
            chart_url=f"https://{base}/chart_{tf}.png?v={int(time.time())}"
            txt=f"🔔 {tf} TEST CANDLE\nOANDA:XAUUSD {tf} Price {price:.2f}\nภูเขา {m['sim']:.0f}% ไม้รวย {r['sim']} เทรน+กรอบ {t['sim']}\nบอท Multi TF ทำงานปกติ"
            import requests
            token=os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"); user_id=os.environ.get("LINE_USER_ID") or os.environ.get("USER_ID")
            headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
            data={"to": user_id, "messages": [{"type":"text","text":txt},{"type":"image","originalContentUrl": chart_url,"previewImageUrl": chart_url}]}
            r=requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data, timeout=15)
            res.append(f"{tf} LINE {r.status_code}")
        return f"<h2>ส่ง Multi TF แล้ว</h2><pre>{chr(10).join(res)}</pre><a href='/home'>home</a>"
    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>",500

def bot_loop():
    time.sleep(5)
    log("Multi TF bot loop M1 M5 M15 M30 started")
    while True:
        try:
            from detector import fetch_gold_data_tf, check_all_patterns
            for tf in TIMEFRAMES:
                try:
                    df=fetch_gold_data_tf(interval=tf)
                    price=float(df['Close'].iloc[-1])
                    m,r,t=check_all_patterns(df)
                    log(f"[{tf}] Price {price:.2f} M{m['sim']:.0f}% R{r['sim']} T{t['sim']} Found {m['found']}/{r['found']}/{t['found']}")
                    if m['found'] or r['found'] or t['found']:
                        generate_chart_tf(df,m,r,t,tf,price)
                        time.sleep(2)
                        base=os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
                        chart_url=f"https://{base}/chart_{tf}.png?v={int(time.time())}"
                        if m['found']:
                            send_line_multi(f"🏔️ [{tf}] ภูเขา 53 {m['sim']:.0f}%\nPrice {price:.2f}\n{m['desc']}", tf)
                        if r['found']:
                            send_line_multi(f"🌲 [{tf}] ไม้รวย BUY Score {r['sim']}\nPrice {price:.2f}\n{r['desc']}", tf)
                        if t['found']:
                            send_line_multi(f"📦 [{tf}] เทรน+ในกรอบ BUY Score {t['sim']}\nPrice {price:.2f}\nกรอบ {t.get('box_low',0):.2f}-{t.get('box_high',0):.2f}\n{t['desc']}", tf)
                except Exception as e:
                    log(f"TF {tf} loop err {e}")
                time.sleep(5)
        except Exception as e:
            log(f"Loop err {e}")
        time.sleep(120)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
