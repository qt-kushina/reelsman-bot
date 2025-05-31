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

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

VIDEO_URL_REGEX = r'(https?://[^\s]+)'
SUPPORTED_DOMAINS = ['instagram.com']

def is_supported_url(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)

def get_direct_video_url(url: str) -> str or None:
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

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
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

@dp.message()
async def handle_video_message(message: Message):
    url_match = re.search(VIDEO_URL_REGEX, message.text or "")
    if not url_match:
        return

    url = url_match.group(1)
    if not is_supported_url(url):
        return

    logging.info(f"[REQUEST] Instagram URL received: {url}")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    direct_url = get_direct_video_url(url)
    if direct_url:
        await message.reply(f"<a href=\"{direct_url}\">ㅤ</a>", parse_mode="HTML")
        logging.info("[RESPONSE] Direct link sent.")
    else:
        await message.reply("Chud Gaye Ghuru 😢")
        logging.warning("[RESPONSE] Extraction failed.")

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Bot info & how to use")
    ])

# Health check endpoint
async def health_check(request):
    return web.Response(text="OK")

async def main():
    await set_commands()

    # Start aiohttp server for Render health check
    app = web.Application()
    app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=int(os.environ.get("PORT", 10000)))
    await site.start()

    logging.info("Bot is live and polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())