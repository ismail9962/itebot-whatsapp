import os
from flask import Flask, request
import requests

app = Flask(__name__)

# متغيرات البيئة من Render
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ITEbotSecure2025")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


# ----------------- دوال مساعدة ----------------- #

def send_whatsapp_message(to, text):
    """
    إرسال رسالة نصية عبر WhatsApp Cloud API
    مع تقطيع الرسائل الطويلة إلى أجزاء
    """
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    max_len = 1500
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]

    for chunk in chunks:
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "text": {"body": chunk}
        }
        resp = requests.post(url, headers=headers, json=data)
        print("WA response:", resp.status_code, resp.text)

def call_gpt(mode: str, user_text: str) -> str:
    """
    استدعاء ChatGPT باستخدام Chat Completions مع الموديل gpt-4o-mini
    """
    if not OPENAI_API_KEY:
        return "❌ لا يوجد OPENAI_API_KEY مضبوط في السيرفر."

    # اختيار الـ system prompt حسب نوع الأمر
    if mode == "analysis":
        system_prompt = (
            "أنت دكتور تحليل رياضي لطلاب السنة الأولى في الهندسة المعلوماتية "
            "في الجامعة الافتراضية السورية (ITE S25). اشرح ببساطة وبخطوات، "
            "مع أمثلة قدر الإمكان، وتجنّب إعطاء حلول جاهزة للوظائف بدون شرح."
        )
    elif mode == "programming":
        system_prompt = (
            "أنت مدرس برمجة C++ لطلاب مبتدئين في الهندسة المعلوماتية – SVU. "
            "اشرح الأكواد والأخطاء بالتفصيل، مع أمثلة صغيرة، وركّز على الفهم."
        )
    elif mode == "physics":
        system_prompt = (
            "أنت مدرس فيزياء جامعية (حركة وميكانيك) لطلاب الهندسة المعلوماتية – SVU. "
            "استخدم شرحاً مبسّطاً وخطوات واضحة وأمثلة من الحياة اليومية."
        )
    elif mode == "english":
        system_prompt = (
            "أنت مدرس لغة إنكليزية لمستوى A2-B1. "
            "صحح الأخطاء، واقترح جمل أفضل، واشرح بالعربي عند الحاجة."
        )
    else:
        system_prompt = (
            "أنت مساعد دراسي عام لطلاب الهندسة المعلوماتية (ITE S25) في الجامعة "
            "الافتراضية السورية. ساعدهم في الشرح وتنظيم الدراسة بدون تشجيع الغش."
        )

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        # لطباعة تفاصيل الخطأ في الـ Logs على Render
        try:
            print("GPT error:", e, r.text)
        except:
            print("GPT error:", e)
        return "❌ حصل خطأ أثناء الاتصال بـ ChatGPT. حاول مرة أخرى لاحقاً."



# ----------------- Webhook استقبال الرسائل ----------------- #

@app.route("/webhook", methods=["POST"])
def webhook():
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
    from_number = msg.get("from")
    text = msg.get("text", {}).get("body", "")

    incoming = text.strip()
    lower = incoming.lower()

    # أوامر ثابتة
    if lower == "/ping":
        send_whatsapp_message(from_number, "✅ ITEbot online – البوت شغال تمام.")
        return "OK", 200

    if lower == "/help":
        reply = (
            "👋 أهلاً بك في ITEbot – مساعد دفعة ITE S25.\n"
            "الأوامر المتاحة:\n"
            "/ping – اختبار عمل البوت\n"
            "/analysis سؤالك… – مساعدة في التحليل الرياضي\n"
            "/programming سؤالك… – مساعدة في البرمجة C++\n"
            "/physics سؤالك… – مساعدة في الفيزياء\n"
            "/english جملتك… – تحسين الإنجليزية\n"
            "/ask سؤالك… – أي سؤال عام دراسي أو تقني\n"
        )
        send_whatsapp_message(from_number, reply)
        return "OK", 200

    # أوامر GPT
    mode = None
    content = None

    if lower.startswith("/analysis"):
        mode = "analysis"
        content = incoming[len("/analysis"):].strip()
    elif lower.startswith("/programming"):
        mode = "programming"
        content = incoming[len("/programming"):].strip()
    elif lower.startswith("/physics"):
        mode = "physics"
        content = incoming[len("/physics"):].strip()
    elif lower.startswith("/english"):
        mode = "english"
        content = incoming[len("/english"):].strip()
    elif lower.startswith("/ask"):
        mode = "general"
        content = incoming[len("/ask"):].strip()

    if mode:
        if not content:
            send_whatsapp_message(
                from_number,
                "ℹ️ اكتب الأمر متبوعاً بسؤالك.\nمثال:\n/analysis ما هي الدالة المتصلة؟"
            )
            return "OK", 200

        gpt_reply = call_gpt(mode, content)
        send_whatsapp_message(from_number, gpt_reply)
        return "OK", 200

    # أي رسالة بدون أوامر
    default_reply = (
        "🤖 ITEbot: استقبلت رسالتك.\n"
        "اكتب /help لعرض قائمة الأوامر المتاحة."
    )
    send_whatsapp_message(from_number, default_reply)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
