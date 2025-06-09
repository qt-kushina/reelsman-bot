import os
import re
import yt_dlp
import asyncio
import logging
from aiohttp import web
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

OWNER_ID = 5290407067
USERS_FILE = "users.txt"
VIDEO_URL_REGEX = r'(https?://[^\s]+)'
SUPPORTED_DOMAINS = ['instagram.com']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_supported_url(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)

def get_direct_video_url(url: str) -> str | None:
    ydl_opts = {
        'format': 'best[height<=720]/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        }
    }
    for attempt in range(2):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logging.info(f"[SUCCESS] Video title: {info.get('title')}")
                return info.get("url")
        except Exception as e:
            logging.warning(f"[RETRY {attempt + 1}] Failed to extract video URL: {e}")
            asyncio.sleep(1)
    logging.error("[FAILURE] All attempts to extract video URL failed.")
    return None

def save_user(user_id: int):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(f"{user_id}\n")
    else:
        with open(USERS_FILE, "r") as f:
            existing_users = f.read().splitlines()
        if str(user_id) not in existing_users:
            with open(USERS_FILE, "a") as f:
                f.write(f"{user_id}\n")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Updates", url="https://t.me/WorkGlows"),
         InlineKeyboardButton("Support", url="https://t.me/TheCryptoElders")],
        [InlineKeyboardButton("Add Me To Your Group",
                              url=f"https://t.me/{context.bot.username}?startgroup=true")]
    ])

    text = (
        "<b>🎬 Instagram Video Downloader</b>\n\n"
        "Send any Instagram video link, and I'll give u a direct download link.\n\n"
        "✅ No bandwidth use\n"
        "❌ Private videos not supported\n\n"
        "Enjoy fast downloads!"
    )
    await update.message.reply_html(text, reply_markup=keyboard)

async def secret_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    content = update.message.text.replace("/send", "", 1).strip()
    if not content:
        await update.message.reply_text("Usage: /send Your message here")
        return

    if not os.path.exists(USERS_FILE):
        await update.message.reply_text("No users to broadcast.")
        return

    sent_count = 0
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()

    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=content)
            sent_count += 1
        except Exception as e:
            logging.warning(f"Failed to send message to {uid}: {e}")

    await update.message.reply_text(f"Message sent to {sent_count} users.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    url_match = re.search(VIDEO_URL_REGEX, text)
    if not url_match:
        return

    url = url_match.group(1)
    if not is_supported_url(url):
        return

    logging.info(f"[REQUEST] Instagram URL received: {url}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    direct_url = get_direct_video_url(url)
    if direct_url:
        await update.message.reply_html(f'<a href="{direct_url}">ㅤ</a>')
        logging.info("[RESPONSE] Direct link sent.")
    else:
        await update.message.reply_text("Chud Gaye Ghuru 😢")
        logging.warning("[RESPONSE] Extraction failed.")

async def health_check(request):
    return web.Response(text="OK")

async def set_commands(bot):
    await bot.set_my_commands([
        BotCommand("start", "Bot info & how to use"),
    ])

async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    await set_commands(application.bot)

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("send", secret_broadcast))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

    # Health check route
    app = web.Application()
    app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=int(os.getenv("PORT", 10000)))
    await site.start()

    logging.info("Bot is live and polling...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())