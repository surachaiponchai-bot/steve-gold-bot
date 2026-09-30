# Steve Gold - 53 Candles Mountain Bot - FREE Cloud Deploy

## Deploy ฟรีบน Render.com (ไม่ต้องเปิดคอม)

1. อัปโหลดโค้ดนี้ขึ้น GitHub:
   - สร้าง repo ใหม่บน github.com
   - อัปโหลดไฟล์ทั้งหมดนี้

2. เข้า https://render.com → New → Web Service → เลือก repo นี้

3. ตั้งค่า:
   - Build Command: pip install -r requirements.txt
   - Start Command: python app.py
   - Plan: Free

4. เพิ่ม Environment Variables:
   - LINE_CHANNEL_TOKEN = ใส่ token ยาวๆ ของคุณ (ตัวที่ส่งได้ 200)
   - PATTERN_THRESHOLD = 55
   - CANDLE_COUNT = 53

5. กด Deploy → รอ 2 นาที → เสร็จ!

Bot จะรัน 24/7 บน Cloud ฟรี ไม่ต้องเปิดคอม

ทดสอบ: เปิด https://your-app.onrender.com/test → จะส่ง LINE ทดสอบทันที

ดูสถานะ: https://your-app.onrender.com/
