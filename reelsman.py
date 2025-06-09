import os
import re
import yt_dlp
import asyncio
import logging
from pathlib import Path
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
)
from aiogram.client.default import DefaultBotProperties

# ───────────────────────────────────────────────────────── CONFIG
BOT_TOKEN  = os.getenv("BOT_TOKEN")
OWNER_ID   = 5290407067
USERS_FILE = Path("users.txt")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp  = Dispatcher()

# ───────────────────────────────────────────────────────── HELPERS
def load_users() -> set[int]:
    return {int(x) for x in USERS_FILE.read_text().splitlines()} if USERS_FILE.exists() else set()

def save_user(chat_id: int) -> None:
    users = load_users()
    if chat_id not in users:
        users.add(chat_id)
        USERS_FILE.write_text("\n".join(map(str, users)))
        logger.info(f"[STORE] New user {chat_id}")

def owner_only(func):
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id != OWNER_ID:
            await message.reply("🚫 Not for you.")
            return
        return await func(message, *args, **kwargs)
    return wrapper

# ───────────────────────────────────────────────────────── URL / yt-dlp
VIDEO_URL_REGEX = r'(https?://(?:www\.)?[^\s]+)'
SUPPORTED_DOMAINS = [
    'instagram.com', 'tiktok.com', 'twitter.com', 'x.com', 'facebook.com', 'fb.watch',
    'youtube.com', 'youtu.be', 'reddit.com', 'pinterest.com', 'threads.net', 'dailymotion.com',
    'likee.video', 'vimeo.com', 'kwai.com', 'bilibili.com', 'streamable.com', 'twitch.tv',
    'tumblr.com', 'triller.co', 'youku.com', 'vk.com', 'odnoklassniki.ru', '9gag.com',
    'imgur.com', 'imdb.com', 'bandcamp.com', 'soundcloud.com', 'mixcloud.com', 'tnaflix.com',
    'pornhub.com', 'xvideos.com', 'xnxx.com', 'spankbang.com', 'onlyfans.com', 'fansly.com',
    'rumble.com', 'bitchute.com', 'peertube.tv', 'tubi.tv', 'vlive.tv', 'funimation.com',
    'crunchyroll.com', 'metacafe.com', 'ted.com', 'brighteon.com', 'odysee.com', 'newgrounds.com',
    'mediasite.com', 'locals.com',
]

def is_supported_url(url: str) -> bool:
    return any(d in url for d in SUPPORTED_DOMAINS)

async def get_direct_video_url(url: str) -> str | None:
    """Return a direct playable URL or None. Retries 3×."""
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
        'retries': 3,
        'geo_bypass': True,
        'http_headers': {'User-Agent': 'Mozilla/5.0'},
    }

    for attempt in range(1, 4):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info.get("url"):
                    return info["url"]
                if info.get("formats"):
                    return info["formats"][0]["url"]
                if info.get("entries"):
                    entry = info["entries"][0]
                    return entry.get("url") or (entry.get("formats") or [{}])[0].get("url")
        except Exception as e:
            logger.warning(f"[RETRY {attempt}] yt-dlp error: {e}")
            await asyncio.sleep(1)

    logger.error(f"[FAIL] Could not extract from {url}")
    return None

# ───────────────────────────────────────────────────────── HANDLERS
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    save_user(message.chat.id)
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Updates", url="https://t.me/WorkGlows"),
         InlineKeyboardButton("Support", url="https://t.me/TheCryptoElders")],
        [InlineKeyboardButton("Add Me To Your Group",
                              url=f"https://t.me/{(await bot.me()).username}?startgroup=true")]
    ])
    await message.answer(
        "<b>🎬 Multi-Platform Video Downloader</b>\n\n"
        "Send any supported link, I'll return a direct download URL.\n"
        "Over 50 sites supported.\n\n"
        "✅ Fast  ❌ Private/paid videos not supported",
        reply_markup=kb
    )

@dp.message(F.text.regexp(r'^/broadcast\s+.+'))
@owner_only
async def cmd_broadcast(message: Message):
    msg = message.text.partition(' ')[2].strip()
    if not msg:
        await message.reply("⚠️ Usage: /broadcast <text>")
        return

    users = load_users()
    sent = failed = 0
    for uid in users:
        try:
            await bot.send_message(uid, msg)
            sent += 1
        except Exception as e:
            logger.warning(f"[BCAST FAIL] {uid}: {e}")
            failed += 1
    await message.reply(f"✅ Sent: {sent}\n❌ Failed: {failed}")

@dp.message()
async def handle_video_message(message: Message):
    save_user(message.chat.id)
    match = re.search(VIDEO_URL_REGEX, message.text or "")
    if not match:
        return
    url = match.group(1)
    if not is_supported_url(url):
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    direct = await get_direct_video_url(url)
    if direct:
        await message.reply(direct, disable_web_page_preview=True)
        logger.info(f"[LINK] Sent for {url}")
    else:
        await message.reply("😢 Couldn't fetch that one. Try again later.")
        logger.error(f"[LINK FAIL] {url}")

# ───────────────────────────────────────────────────────── STARTUP & HEALTH
async def set_commands():
    try:
        await bot.set_my_commands(
            commands=[
                BotCommand(command="start", description="Bot info & how to use"),
                BotCommand(command="broadcast", description="(owner) send message"),
            ]
        )
    except Exception as e:
        logger.error(f"[COMMANDS] Failed to set commands: {e}")

async def health_check(_): 
    return web.Response(text="OK")

async def main():
    await set_commands()
    app = web.Application(); app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, port=int(os.getenv("PORT", 10000))); await site.start()
    logger.info("Bot is live…")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())