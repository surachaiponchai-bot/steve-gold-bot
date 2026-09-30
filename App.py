from flask import Flask, send_file
import os, time, threading, traceback
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CHART_DIR = "/tmp"
TIMEFRAMES = ["1m", "5m", "15m", "30m"]
# เก็บ cache ราคา ลดการดึงซ้ำ
cache = {"data":{}, "last_fetch":0}

def log(msg): print(msg, flush=True)

def generate_chart_fast(df, m, r, t, tf_label, price):
    try:
        plot_df = df.tail(50).copy().reset_index(drop=True) # ลดเหลือ 50 แท่ง เร็วขึ้น
        path = f"{CHART_DIR}/chart_{tf_label}.png"
        fig, ax = plt.subplots(figsize=(10,4.5), dpi=120) # ลด dpi จาก 200 -> 120 เร็วขึ้น 60%
        fig.patch.set_facecolor('#0a0a0a')
        ax.set_facecolor('#0a0a0a')
        for i in range(len(plot_df)):
            o=float(plot_df['Open'].iloc[i]); h=float(plot_df['High'].iloc[i]); l=float(plot_df['Low'].iloc[i]); c=float(plot_df['Close'].iloc[i])
            is_bull=c>=o; color='#26a69a' if is_bull else '#ef5350'
            ax.plot([i,i],[l,h], color=color, linewidth=0.8, alpha=0.9, zorder=1)
            body_bottom=min(o,c); body_height=abs(c-o)
            if body_height < (h-l)*0.05:
                body_height=(h-l)*0.05; body_bottom=(o+c)/2-body_height/2
            rect=mpatches.Rectangle((i-0.3, body_bottom),0.6, body_height if body_height>0 else 0.2, facecolor=color, edgecolor=color, linewidth=0.8, zorder=2, alpha=0.95)
            ax.add_patch(rect)
        # ไม่วาด EMA ถ้าไม่จำเป็น - เร็วขึ้นอีก
        if t and 'box_low' in t and t.get('sim',0)>40:
            try:
                box_low=float(t['box_low']); box_high=float(t['box_high']); box_len=12; start_idx=len(plot_df)-box_len-1
                ax.fill_between([start_idx, len(plot_df)-1], box_low, box_high, color='#00e5ff', alpha=0.12)
                ax.plot([start_idx, len(plot_df)-1],[box_low,box_low], color='#00e5ff', linestyle='--', linewidth=1.2)
                ax.plot([start_idx, len(plot_df)-1],[box_high,box_high], color='#00e5ff', linestyle='--', linewidth=1.2)
            except: pass
        ax.set_title(f"{tf_label} {price:.2f} M{m['sim']:.0f}% R{r['sim']} T{t['sim']} {datetime.now().strftime('%H:%M:%S')}", color='white', fontsize=9, fontweight='bold', loc='left')
        ax.grid(True, alpha=0.1, color='gray', linestyle='--')
        ax.tick_params(colors='white', labelsize=7)
        for spine in ax.spines.values(): spine.set_color('#333333')
        low=plot_df['Low'].min(); high=plot_df['High'].max(); pad=(high-low)*0.12
        ax.set_xlim(-1, len(plot_df)); ax.set_ylim(low-pad, high+pad)
        plt.tight_layout()
        plt.savefig(path, facecolor='#0a0a0a', bbox_inches='tight')
        plt.close()
        return path
    except Exception as e:
        log(f"Chart {tf_label} err {e}"); return None

def send_line_multi(text, tf_label):
    try:
        import requests
        token=os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN") or os.environ.get("LINE_ACCESS_TOKEN")
        user_id=os.environ.get("LINE_USER_ID") or os.environ.get("USER_ID")
        if not token or not user_id: return
        base=os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
        chart_url=f"https://{base}/chart_{tf_label}.png?v={int(time.time())}"
        headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
        data={"to": user_id, "messages": [{"type":"text","text":text},{"type":"image","originalContentUrl": chart_url,"previewImageUrl": chart_url}]}
        r=requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data, timeout=10)
        log(f"PUSH {tf_label} {r.status_code}")
    except Exception as e:
        log(f"send err {e}")

@app.route('/')
def root(): return "FAST Multi TF - /home"

@app.route('/home')
def home():
    try:
        from detector import fetch_gold_data_tf, check_all_patterns
        html="<h2>Steve Gold FAST Multi TF M1 M5 M15 M30</h2><p>Optimized FAST mode - check 4 TF parallel</p>"
        # ดึง parallel เร็ว x4
        def fetch_tf(tf):
            df=fetch_gold_data_tf(interval=tf)
            price=float(df['Close'].iloc[-1])
            m,r,t=check_all_patterns(df)
            return tf, df, price, m, r, t
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures={executor.submit(fetch_tf, tf): tf for tf in TIMEFRAMES}
            results={}
            for fut in as_completed(futures):
                try:
                    tf, df, price, m, r, t = fut.result()
                    results[tf]=(df, price, m, r, t)
                except Exception as e:
                    log(f"fetch {futures[fut]} err {e}")
        
        for tf in TIMEFRAMES:
            if tf in results:
                df, price, m, r, t = results[tf]
                # วาดกราฟเฉพาะถ้ามีสัญญาณหรือหน้า home เท่านั้น (หน้า home วาดอยู่ดี)
                generate_chart_fast(df,m,r,t,tf,price)
                html+=f"<h3>{tf} Price {price:.2f} Mtn {m['sim']:.0f}% R {r['sim']} T {t['sim']} Found {m['found']}/{r['found']}/{t['found']}</h3>"
                html+=f"<img src='/chart_{tf}.png?v={int(time.time())}' style='width:100%;max-width:900px'><hr>"
        return html
    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>",500

@app.route('/chart_<tf>.png')
def chart_tf(tf):
    p=f"{CHART_DIR}/chart_{tf}.png"
    if os.path.exists(p): return send_file(p, mimetype='image/png')
    return "No chart",404

@app.route('/chart.png')
def chart_default(): return chart_tf('5m')

@app.route('/test_line')
def test_line():
    try:
        from detector import fetch_gold_data_tf, check_all_patterns
        res=[]
        def fetch_and_send(tf):
            df=fetch_gold_data_tf(interval=tf)
            price=float(df['Close'].iloc[-1])
            m,r,t=check_all_patterns(df)
            generate_chart_fast(df,m,r,t,tf,price)
            base=os.environ.get('RENDER_EXTERNAL_HOSTNAME','steve-gold-bot.onrender.com')
            chart_url=f"https://{base}/chart_{tf}.png?v={int(time.time())}"
            import requests
            token=os.environ.get("LINE_TOKEN") or os.environ.get("LINE_CHANNEL_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
            user_id=os.environ.get("LINE_USER_ID") or os.environ.get("USER_ID")
            txt=f"🔔 {tf} FAST TEST {price:.2f} M{m['sim']:.0f}% R{r['sim']} T{t['sim']}"
            headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
            data={"to": user_id, "messages": [{"type":"text","text":txt},{"type":"image","originalContentUrl": chart_url,"previewImageUrl": chart_url}]}
            r=requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data, timeout=10)
            return f"{tf} {r.status_code}"
        
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs=[ex.submit(fetch_and_send, tf) for tf in TIMEFRAMES]
            for f in as_completed(futs):
                res.append(f.result())
        return f"<h2>FAST Multi TF sent</h2><pre>{chr(10).join(res)}</pre>"
    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>",500

def bot_loop():
    time.sleep(5)
    log("FAST Multi TF bot started - parallel fetch")
    while True:
        try:
            from detector import fetch_gold_data_tf, check_all_patterns
            def check_tf(tf):
                try:
                    df=fetch_gold_data_tf(interval=tf)
                    price=float(df['Close'].iloc[-1])
                    m,r,t=check_all_patterns(df)
                    log(f"[{tf}] {price:.2f} M{m['sim']:.0f}% R{r['sim']} T{t['sim']} {m['found']}/{r['found']}/{t['found']}")
                    if m['found'] or r['found'] or t['found']:
                        generate_chart_fast(df,m,r,t,tf,price)
                        time.sleep(1)
                        if m['found']: send_line_multi(f"🏔️ [{tf}] ภูเขา {m['sim']:.0f}%\nPrice {price:.2f}\n{m['desc']}", tf)
                        if r['found']: send_line_multi(f"🌲 [{tf}] ไม้รวย BUY {r['sim']}\nPrice {price:.2f}\n{r['desc']}", tf)
                        if t['found']: send_line_multi(f"📦 [{tf}] เทรน+กรอบ BUY {t['sim']}\nPrice {price:.2f}\nBox {t.get('box_low',0):.2f}-{t.get('box_high',0):.2f}", tf)
                    return tf
                except Exception as e:
                    log(f"TF {tf} err {e}")
                    return tf
            
            # ดึงพร้อมกัน 4 TF เร็ว x4
            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(check_tf, TIMEFRAMES))
                
        except Exception as e:
            log(f"Loop err {e}")
        time.sleep(90)  # เช็คทุก 90 วิ แทน 120 วิ เร็วขึ้น

threading.Thread(target=bot_loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
