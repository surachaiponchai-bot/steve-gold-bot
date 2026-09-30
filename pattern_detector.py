
import numpy as np
import pandas as pd

def check_53_mountain(df_53):
    """
    เช็ค 53 แท่งปัจจุบันว่าเป็นภูเขาไหม
    รูปแบบ: เริ่มต่ำ -> ขึ้นไปพีคกลาง -> ลงกลับต่ำ
    เหมือนรูปที่คุณวงเขียวไว้
    """
    if len(df_53) < 53:
        return {'found': False, 'similarity': 0, 'reason': f'มีแค่ {len(df_53)} แท่ง ไม่ครบ 53'}
    
    closes = df_53['Close'].values
    highs = df_53['High'].values if 'High' in df_53.columns else closes
    lows = df_53['Low'].values if 'Low' in df_53.columns else closes
    
    # แบ่ง 53 แท่งเป็น 3 ช่วง: ต้น(15) กลาง(23) ท้าย(15)
    start = closes[:15]
    middle = closes[15:38]
    end = closes[38:]
    
    start_low = np.min(lows[:15])
    middle_high = np.max(highs[15:38])
    end_low = np.min(lows[38:])
    
    start_avg = np.mean(start)
    middle_avg = np.mean(middle)
    end_avg = np.mean(end)
    
    # เช็คภูเขา: กลางสูงกว่า เริ่มและท้าย
    height1 = middle_high - start_low
    height2 = middle_high - end_low
    
    if height1 <= 0 or height2 <= 0:
        return {'found': False, 'similarity': 10, 'reason': 'ไม่เป็นภูเขา กลางไม่สูงกว่าขอบ'}
    
    # ความสมมาตรของฐาน
    base_diff = abs(start_low - end_low) / ((start_low + end_low)/2) * 100
    base_similarity = max(0, 100 - base_diff*20)
    
    # ความสูงของภูเขา
    avg_range = (height1 + height2) / 2
    price_range = middle_high - min(start_low, end_low)
    # ต้องสูงพอ (0.1% ขึ้นไป)
    height_pct = avg_range / closes[-1] * 100
    height_score = min(100, height_pct * 200)  # 0.5% = 100 คะแนน
    
    # เช็คว่ากลางเป็นพีคจริงไหม (ต้องสูงกว่าค่าเฉลี่ยเริ่มและท้าย)
    middle_peak_score = 0
    if middle_avg > start_avg and middle_avg > end_avg:
        middle_peak_score = min(100, (middle_avg - max(start_avg, end_avg)) / middle_avg * 100 * 10)
    
    # รวมคะแนนความเหมือนภูเขา
    similarity = (base_similarity*0.3 + height_score*0.4 + middle_peak_score*0.3)
    
    # เพิ่มคะแนนถ้าเป็นทรงสามเหลี่ยมสวย
    # สร้างทรงภูเขาในอุดมคติแล้วเทียบ correlation
    ideal = np.concatenate([
        np.linspace(0, 1, 26),  # ขึ้น
        np.linspace(1, 0, 27)   # ลง
    ])
    # normalize closes
    norm_closes = (closes - np.min(closes)) / (np.max(closes) - np.min(closes) + 1e-9)
    corr = np.corrcoef(norm_closes, ideal)[0,1]
    if np.isnan(corr):
        corr = 0
    corr_score = max(0, corr) * 100
    similarity = similarity*0.6 + corr_score*0.4
    
    is_mountain = similarity >= 65 and height_pct > 0.05
    
    return {
        'found': bool(is_mountain),
        'similarity': float(similarity),
        'type': 'ภูเขา 53 แท่ง',
        'valley1': float(start_low),
        'peak': float(middle_high),
        'valley2': float(end_low),
        'height_pct': float(height_pct),
        'base_diff_pct': float(base_diff),
        'correlation': float(corr*100),
        'start_avg': float(start_avg),
        'middle_avg': float(middle_avg),
        'end_avg': float(end_avg),
        'description': f'53 แท่ง {start_low:.2f} -> {middle_high:.2f} -> {end_low:.2f} สูง {height_pct:.3f}% เหมือน {similarity:.0f}% corr {corr*100:.0f}%',
        'closes': closes  # สำหรับวาดกราฟ
    }
