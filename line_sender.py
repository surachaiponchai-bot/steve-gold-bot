
import requests
from config import LINE_CHANNEL_TOKEN, LINE_USER_ID

def upload_image_to_host(image_path):
    try:
        print("Uploading to catbox.moe...")
        with open(image_path, 'rb') as f:
            r = requests.post("https://catbox.moe/user/api.php", data={'reqtype':'fileupload'}, files={'fileToUpload': f}, timeout=30)
        if r.status_code == 200 and r.text.strip().startswith("https"):
            url = r.text.strip()
            print(f"  OK: {url}")
            return url
    except Exception as e:
        print(f"  Upload error: {e}")
    return None

def _send_payload(payload):
    url_broadcast = "https://api.line.me/v2/bot/message/broadcast"
    url_push = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_TOKEN}", "Content-Type": "application/json"}
    if LINE_USER_ID and LINE_USER_ID.startswith("U"):
        payload["to"] = LINE_USER_ID
        url = url_push
        print(f"Using PUSH to {LINE_USER_ID}")
    else:
        url = url_broadcast
        print("Using BROADCAST")
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    print(f"LINE Status: {r.status_code} - {r.text}")
    return r.status_code == 200

def send_line_text(message):
    payload = {"messages": [{"type": "text", "text": message}]}
    return _send_payload(payload)

def send_line_text_and_image(text_message, image_path):
    image_url = upload_image_to_host(image_path)
    if not image_url:
        print("Upload failed, sending text only")
        return send_line_text(text_message + f"\nChart: {image_path}")
    payload = {
        "messages": [
            {"type": "text", "text": text_message},
            {"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url}
        ]
    }
    return _send_payload(payload)
