import os
import re
import yt_dlp
import asyncio
import logging
from pathlib import Path                 # NEW
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.client.default import DefaultBotProperties

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN")
OWNER_ID   = 5290407067                       # << your Telegram user-id
USERS_FILE = Path("users.txt")                # simple persistent storage

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp  = Dispatcher()

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def load_users() -> set[int]:
    if USERS_FILE.exists():
        return {int(x) for x in USERS_FILE.read_text().splitlines() if x.strip().isdigit()}
    return set()

def save_user(chat_id: int) -> None:
    users = load_users()
    if chat_id not in users:
        users.add(chat_id)
        USERS_FILE.write_text("\n".join(str(uid) for uid in users))
        logger.info(f"[STORE] Added new user {chat_id}")

def owner_only(func):
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id != OWNER_ID:
            await message.reply("🚫 Not for you.")
            return
        return await func(message, *args, **kwargs)
    return wrapper

# ──────────────────────────────────────────────────────────────────────────────
# URL-GRAB LOGIC (unchanged, trimmed for brevity)
# ──────────────────────────────────────────────────────────────────────────────
VIDEO_URL_REGEX = r'(https?://[^\s]+)'
SUPPORTED_DOMAINS = [
    'instagram.com',
    'tiktok.com',
    'twitter.com',
    'x.com',
    'facebook.com',
    'fb.watch',
    'youtube.com',
    'youtu.be',
    'reddit.com',
    'pinterest.com',
    'threads.net',
    'dailymotion.com',
    'likee.video',
    'vimeo.com',
    'kwai.com',
    'bilibili.com',
    'streamable.com',
    'twitch.tv',
    'tumblr.com',
    'triller.co',
    'youku.com',
    'vk.com',
    'odnoklassniki.ru',
    '9gag.com',
    'imgur.com',
    'imdb.com',
    'bandcamp.com',
    'soundcloud.com',
    'mixcloud.com',
    'tnaflix.com',
    'pornhub.com',
    'xvideos.com',
    'xnxx.com',
    'spankbang.com',
    'onlyfans.com',
    'fansly.com',
    'rumble.com',
    'bitchute.com',
    'peertube.tv',
    'tubi.tv',
    'vlive.tv',
    'funimation.com',
    'crunchyroll.com',
    'metacafe.com',
    'ted.com',
    'brighteon.com',
    'odysee.com',
    'newgrounds.com',
    'mediasite.com',
    'locals.com',
]

def is_supported_url(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)

def get_direct_video_url(url: str) -> str | None:
    ydl_opts = {
        'format': 'best[height<=1080]/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'http_headers': {'User-Agent': 'Mozilla/5.0'},
    }
    for attempt in range(2):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.info(f"[SUCCESS] {info.get('title')}")
                return info.get("url")
        except Exception as e:
            logger.warning(f"[RETRY {attempt+1}] {e}")
            await asyncio.sleep(1)
    logger.error("[FAILURE] Extraction failed")
    return None

# ──────────────────────────────────────────────────────────────────────────────
# HANDLERS
# ──────────────────────────────────────────────────────────────────────────────
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    save_user(message.chat.id)                       # ← NEW
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Updates", url="https://t.me/WorkGlows"),
         InlineKeyboardButton(text="Support", url="https://t.me/TheCryptoElders")],
        [InlineKeyboardButton(
            text="Add Me To Your Group",
            url=f"https://t.me/{(await bot.me()).username}?startgroup=true")]
    ])

    await message.answer(
        "<b>🎬 Multi-Platform Video Downloader</b>\n\n"
        "Send any supported video link and I'll drop u a direct download link.\n"
        "Currently supports 50+ sites.\n\n"
        "✅ Fast ❌ Private content not supported",
        reply_markup=keyboard
    )

@dp.message(F.text.regexp(r'^/broadcast\s+.+'))
@owner_only                                          # ← NEW
async def cmd_broadcast(message: Message):
    """Owner-only: /broadcast your text"""
    broadcast_text = message.text.partition(' ')[2].strip()
    if not broadcast_text:
        await message.reply("⚠️ Usage: /broadcast <text>")
        return

    users = load_users()
    sent, failed = 0, 0
    for uid in users:
        try:
            await bot.send_message(uid, broadcast_text)
            sent += 1
        except Exception as e:
            logger.warning(f"[BCAST FAIL] {uid}: {e}")
            failed += 1
    await message.reply(f"✅ Sent: {sent}\n❌ Failed: {failed}")

@dp.message()
async def handle_video_message(message: Message):
    save_user(message.chat.id)                       # ← NEW (captures non-/start users)
    url_match = re.search(VIDEO_URL_REGEX, message.text or "")
    if not url_match:
        return
    url = url_match.group(1)
    if not is_supported_url(url):
        return
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    direct_url = get_direct_video_url(url)
    if direct_url:
        await message.reply(f"<a href='{direct_url}'>ㅤ</a>", parse_mode="HTML")
    else:
        await message.reply("😢 Couldn't extract that one.")

# ──────────────────────────────────────────────────────────────────────────────
# STARTUP & HEALTH
# ──────────────────────────────────────────────────────────────────────────────
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Bot info & how to use"),
        BotCommand(command="broadcast", description="(owner) send msg"),   # shows only to you
    ])

async def health_check(request): return web.Response(text="OK")

async def main():
    await set_commands()
    app = web.Application(); app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, port=int(os.getenv("PORT", 10000))); await site.start()
    logger.info("Bot is live…"); await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())