import os
from flask import Flask, request
import requests

app = Flask(__name__)

# القيم تأتي من متغيرات البيئة في Render
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ITEbotSecure2025")


def send_whatsapp_message(to, text):
    """
    إرسال رسالة نصية عبر WhatsApp Cloud API
    """
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }
    resp = requests.post(url, headers=headers, json=data)
    print("WA response:", resp.status_code, resp.text)


@app.route("/webhook", methods=["GET"])
def verify():
    """
    تحقق Webhook – Meta تستدعيه أول مرة
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Error: invalid token", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    استقبال رسائل واتساب والرد عليها
    """
    data = request.get_json()
    print("Incoming:", data)

    entry = data.get("entry", [])
    if not entry:
        return "OK", 200

    changes = entry[0].get("changes", [])
    if not changes:
        return "OK", 200

    value = changes[0].get("value", {})
    messages = value.get("messages", [])

    if not messages:
        return "OK", 200

    msg = messages[0]
    from_number = msg.get("from")               # رقم المرسل
    text = msg.get("text", {}).get("body", "")  # نص الرسالة

    incoming = text.strip().lower()

    if incoming == "/help":
        reply = (
            "👋 أهلاً بك في ITEbot – مساعد دفعة ITE S25.\n"
            "الأوامر المتاحة حالياً:\n"
            "/help – عرض هذه المساعدة\n"
            "/ping – اختبار عمل البوت\n"
            "لاحقاً سيتم إضافة أوامر التحليل والبرمجة والفيزياء 🤖"
        )
    elif incoming == "/ping":
        reply = "✅ البوت شغال تمام! ITEbot online."
    else:
        reply = (
            "🤖 ITEbot: استقبلت رسالتك.\n"
            "اكتب /help لعرض الأوامر المتاحة.\n"
            "قريباً سأساعدك في مواد التحليل، البرمجة والفيزياء إن شاء الله."
        )

    send_whatsapp_message(from_number, reply)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
