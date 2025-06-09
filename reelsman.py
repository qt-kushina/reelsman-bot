import os
import re
import yt_dlp
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.client.default import DefaultBotProperties

# Bot token and owner ID
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 5290407067

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot & Dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Regex and supported domains
VIDEO_URL_REGEX = (
    r"(https?://(?:www\.)?instagram\.com/"
    r"(?:reel|reels|tv|p|stories|reels/audio)/[^\s/?#&]+)"
)

SUPPORTED_DOMAINS = [
    "instagram.com/reel/",
    "instagram.com/reels/",
    "instagram.com/reels/audio/",
    "instagram.com/p/",
    "instagram.com/stories/",
    "instagram.com/tv/",
]

# Global set to store user IDs
user_ids = set()

# URL validation
def is_supported_url(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)

# Clean Instagram URL
def clean_instagram_url(url: str) -> str:
    return url.split('?')[0]

# Infinite retry to get video
async def get_direct_video_url(url: str) -> str:
    ydl_opts = {
        'format': 'best[height<=1080]/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        }
    }
    attempt = 0
    while True:
        attempt += 1
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logging.info(f"[SUCCESS] Video title: {info.get('title')}")
                return info.get("url")
        except Exception as e:
            logging.warning(f"[RETRY {attempt}] Failed to extract video URL: {e}")
            await asyncio.sleep(1)

# /start handler
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    user_ids.add(message.from_user.id)
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Updates", url="https://t.me/WorkGlows"),
            InlineKeyboardButton(text="Support", url="https://t.me/TheCryptoElders")
        ],
        [
            InlineKeyboardButton(
                text="Add Me To Your Group",
                url=f"https://t.me/{(await bot.me()).username}?startgroup=true"
            )
        ]
    ])

    text = (
        "<b>🎬 Instagram Video Downloader</b>\n\n"
        "Send any Instagram video link, and I'll give u a direct download link.\n\n"
        "✅ No bandwidth use\n"
        "❌ Private videos not supported\n\n"
        "Enjoy fast downloads!"
    )
    await message.answer(text, reply_markup=keyboard)

# Handle video messages
@dp.message()
async def handle_video_message(message: Message):
    user_ids.add(message.from_user.id)
    mtext = message.text or ""
    match = re.search(VIDEO_URL_REGEX, mtext)
    if not match:
        return

    url = clean_instagram_url(match.group(1))
    if not is_supported_url(url):
        return

    logging.info("📥 URL received: %s", url)
    await bot.send_chat_action(message.chat.id, ChatAction.RECORD_VIDEO)

    direct_url = await get_direct_video_url(url)
    await message.reply(f'<a href="{direct_url}">ㅤ</a>', parse_mode="HTML")
    logging.info("🎯 Direct link delivered.")

# Secret /send command for owner to broadcast
@dp.message(F.text.startswith("/send"))
async def secret_broadcast(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.reply("Usage: /send <message>")
        return

    msg_to_send = parts[1]
    success, fail = 0, 0

    for uid in user_ids.copy():
        try:
            await bot.send_message(uid, msg_to_send)
            success += 1
        except Exception as e:
            logging.warning(f"❌ Failed to send to {uid}: {e}")
            fail += 1

    await message.reply(f"✅ Sent: {success}, ❌ Failed: {fail}")

# Set commands (only /start publicly)
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Bot info & how to use")
    ])

# Health check endpoint
async def health_check(request):
    return web.Response(text="OK")

# Main function
async def main():
    await set_commands()

    # Start aiohttp server
    app = web.Application()
    app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=int(os.environ.get("PORT", 10000)))
    await site.start()

    logging.info("✅ Bot is live and polling...")
    await dp.start_polling(bot)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())