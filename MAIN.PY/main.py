import os
import re
from flask import Flask
from threading import Thread
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

flask_app = Flask('')

@flask_app.route('/')
def home():
    return "NotTodayAI is alive ⚡"

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000, use_reloader=False)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

MAX_LENGTH = 4000

CRISIS_KEYWORDS = [
    r"\bkill myself\b", r"\bi want to die\b", r"\bwant to die\b",
    r"\bi don't want to live\b", r"\bi dont want to live\b",
    r"\bsuicide\b", r"\bsuicidal\b", r"\bhaving suicidal thoughts\b",
    r"\bsuicidal thoughts\b", r"\bi feel suicidal\b", r"\bi am suicidal\b",
    r"\bim suicidal\b", r"\bsuicidal ideation\b",
    r"\bend my life\b", r"\bend it all\b", r"\bi can't go on\b",
    r"\bi cant go on\b", r"\bi want to end\b", r"\bi'm done\b",
    r"\bhang myself\b", r"\bworthless\b", r"\bno reason to live\b",
    r"\bsick of living\b", r"\bi want it to end\b",
    r"\bself harm\b", r"\bself-harm\b", r"\bhurt myself\b",
    r"\bi want to harm myself\b", r"\bplanning to hurt myself\b",
    r"\bcutting myself\b", r"\bcut myself\b", r"\bgoing to kill\b",
    r"\bthinking about suicide\b", r"\bi'm suicidal\b",
    r"\btake my own life\b", r"\btaking my own life\b",
    r"\bthinking of ending\b", r"\bplan to kill\b",
    r"\bthinking of killing\b", r"\bplanning to kill\b"
]
CRISIS_PATTERNS = [re.compile(p, re.I) for p in CRISIS_KEYWORDS]

def detect_crisis(text: str) -> bool:
    if not text:
        return False
    for pat in CRISIS_PATTERNS:
        if pat.search(text):
            return True
    return False

SUPPORT_MESSAGE = (
    "Hey — I hear you and I'm really worried by what you just said. "
    "If you are thinking about hurting yourself or feel like you might, please reach out to someone *right now*. "
    "Call your local emergency number or a suicide prevention hotline if you can. "
    "If you want, tell me whether you are safe right now. I can help you find help or share steps to stay safe."
)

async def send_long_message(bot, chat_id, text):
    for i in range(0, len(text), MAX_LENGTH):
        await bot.send_message(chat_id, text[i:i+MAX_LENGTH])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "🔥 NotTodayAI is online!\n\nUse /ask <your message> to talk to me.\nExample: /ask How to stay focused?"
        )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("❓ Use /ask <your question>")
        return

    if detect_crisis(query):
        await send_long_message(context.bot, update.message.chat_id, SUPPORT_MESSAGE)
        return

    await update.message.reply_text("💭 Thinking...")
    try:
        response = model.generate_content(query)
        await send_long_message(context.bot, update.message.chat_id, response.text)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

async def reply_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id

    if detect_crisis(user_text):
        await send_long_message(context.bot, chat_id, SUPPORT_MESSAGE)
        return

    prompt = (
        "You are NotTodayAI — a hardcore no-excuses motivational coach. "
        "Reply short, fierce, no empathy for excuses, push to action. "
        "Examples: 'Fuck your tiredness. Do the work.' 'Stop whining. Move now.' "
        f"\n\nUser: {user_text}\nNotTodayAI:"
    )

    try:
        lowered = user_text.lower()
        if any(w in lowered for w in ["tired", "lazy", "don't wanna", "dont wanna", "i don't want", "i dont want", "i'm tired", "im tired", "procrastin"]):
            canned = "Fuck your tiredness. Do the work now. No excuses."
            await send_long_message(context.bot, chat_id, canned)
            return

        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        if not text:
            text = "Get after it. No excuses."
        await send_long_message(context.bot, chat_id, text)
    except Exception as e:
        await send_long_message(context.bot, chat_id, "I'm having trouble responding right now. If you need support, please reach out to someone you trust or a helpline.")

app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ask", ask))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_any))

keep_alive()
print("✅ NotTodayAI is running... Type /start in Telegram.")
app.run_polling()
