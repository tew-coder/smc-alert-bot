"""
SMC Alert Bot v1.0 — by Tew
รับ Webhook จาก TradingView → ส่งแจ้งเตือนสวยงามไปยัง Telegram
"""

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")


def parse_alert(raw: str) -> str:
    """
    แปลง TradingView alert string → Telegram message สวยงาม
    Format: LONG GO|XAUUSD|E:2345.50|SL:2335.20(102p)|TP:2366.10|RT:2338.00[IN]|P:78%[A]|R:$10.20(3.4%)|RR:2:1|LONDON|DXY:BEAR
    """
    parts = raw.strip().split("|")
    if len(parts) < 3:
        return f"⚠️ SMC Alert\n{raw}"

    direction_raw = parts[0]  # e.g. "LONG GO" or "SHORT WAIT"
    is_long  = "LONG"  in direction_raw
    is_go    = "GO"    in direction_raw

    dir_emoji  = "🟢" if is_long  else "🔴"
    go_emoji   = "✅" if is_go    else "⏳"
    dir_label  = "LONG"  if is_long  else "SHORT"
    go_label   = "GO — เข้าได้เลย!" if is_go else "WAIT — รอ Retest"

    lines = [
        f"{dir_emoji} *SMC v12 Signal — {dir_label}*",
        f"{go_emoji} *{go_label}*",
        "",
    ]

    field_map = {
        "E":   ("📍", "Entry"),
        "SL":  ("🛑", "Stop Loss"),
        "TP":  ("🎯", "Take Profit"),
        "RT":  ("🔄", "Retest Zone"),
        "P":   ("📊", "Probability"),
        "R":   ("💰", "Risk"),
        "RR":  ("⚖️",  "RR Ratio"),
        "DXY": ("💵", "DXY"),
    }

    sessions = {"LONDON", "NEW YORK", "ASIA", "LOW VOL"}

    for part in parts[1:]:
        part = part.strip()
        if ":" in part:
            key, val = part.split(":", 1)
            key = key.strip()
            if key in field_map:
                em, label = field_map[key]
                lines.append(f"{em} {label}: `{val}`")
        elif part in sessions:
            lines.append(f"🕐 Session: `{part}`")

    lines.append("")
    lines.append("_— SMC Predictor by Tew v12_")
    return "\n".join(lines)


def send_telegram(text: str) -> dict:
    if not BOT_TOKEN or not CHAT_ID:
        return {"ok": False, "error": "BOT_TOKEN or CHAT_ID not set"}
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    CHAT_ID,
        "text":       text,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.route("/webhook", methods=["POST"])
def webhook():
    """TradingView ส่ง POST มาที่ /webhook"""
    raw = request.get_data(as_text=True)
    if not raw:
        return jsonify({"ok": False, "error": "empty body"}), 400

    message  = parse_alert(raw)
    result   = send_telegram(message)
    return jsonify({"ok": True, "raw": raw, "telegram": result})


@app.route("/test", methods=["GET"])
def test():
    """ทดสอบ bot ด้วย Signal จำลอง"""
    sample = "LONG GO|XAUUSD|E:2345.50|SL:2335.20(102p)|TP:2366.10|RT:2338.00[IN]|P:78%[A]|R:$10.20(3.4%)|RR:2:1|LONDON|DXY:BEAR"
    message = parse_alert(sample)
    result  = send_telegram(message)
    return jsonify({"ok": True, "message": message, "telegram": result})


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "SMC Alert Bot running", "version": "1.0"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
