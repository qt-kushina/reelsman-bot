import os
import re
import yt_dlp
import asyncio
import logging
import time
from typing import Optional, List, Callable, Dict, Any, Awaitable
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction
from aiogram.utils.markdown import hbold
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.session.aiohttp import AiohttpSession

# ─── Imports for Dummy HTTP Server ──────────────────────────────────────────
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

OWNER_ID = 5290407067
USERS_FILE = "users.txt"
VIDEO_URL_REGEX = r'(https?://[^\s]+)'
SUPPORTED_DOMAINS = ['instagram.com', 'www.instagram.com']
WEBHOOK_PORT = int(os.getenv("PORT", 8000))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# User Management Functions
async def save_user(user_id: int) -> bool:
    """Save user ID to file if not already present"""
    try:
        existing_users = set()
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                existing_users = set(line.strip() for line in f if line.strip())
        
        if str(user_id) not in existing_users:
            with open(USERS_FILE, "a") as f:
                f.write(f"{user_id}\n")
            logger.info(f"New user saved: {user_id}")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error saving user {user_id}: {e}")
        return False

async def get_all_users() -> Optional[List[int]]:
    """Get all user IDs from file"""
    try:
        if not os.path.exists(USERS_FILE):
            return []
        
        with open(USERS_FILE, "r") as f:
            users = []
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    users.append(int(line))
            
            return users
    
    except Exception as e:
        logger.error(f"Error reading users file: {e}")
        return None

# Instagram URL Processing
def is_supported_url(url: str) -> bool:
    """Check if URL is from a supported domain"""
    return any(domain in url.lower() for domain in SUPPORTED_DOMAINS)

async def get_direct_video_url(url: str) -> Optional[str]:
    """Extract direct video URL from Instagram link"""
    ydl_opts = {
        'format': 'best[height<=720]/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36',
        },
        'cookiefile': None,
        'extract_flat': False,
    }
    
    for attempt in range(3):
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                _extract_video_info,
                url,
                ydl_opts
            )
            
            if result:
                logger.info(f"[SUCCESS] Video extracted: {result.get('title', 'Unknown')}")
                return result.get("url")
            
        except Exception as e:
            logger.warning(f"[RETRY {attempt + 1}/3] Failed to extract video URL: {e}")
            if attempt < 2:
                await asyncio.sleep(1)
    
    logger.error(f"[FAILURE] All attempts failed for URL: {url}")
    return None

def _extract_video_info(url: str, ydl_opts: dict) -> Optional[dict]:
    """Extract video info using yt-dlp (blocking operation)"""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logger.error(f"yt-dlp extraction error: {e}")
        return None

# Logging Middleware
class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging message processing"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        
        user_info = f"@{event.from_user.username}" if event.from_user.username else f"ID:{event.from_user.id}"
        chat_type = event.chat.type
        message_type = "text" if event.text else "other"
        
        logger.info(
            f"📨 Message from {user_info} in {chat_type} chat | Type: {message_type}"
        )
        
        try:
            result = await handler(event, data)
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"⚡ Message processed in {processing_time:.2f}ms")
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Error processing message in {processing_time:.2f}ms: {e}")
            raise

# Bot Handlers
commands_router = Router()
messages_router = Router()

@commands_router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    await save_user(user_id)
    
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Updates", url="https://t.me/WorkGlows"),
            InlineKeyboardButton(text="💬 Support", url="https://t.me/TheCryptoElders")
        ],
        [
            InlineKeyboardButton(
                text="➕ Add Me To Your Group",
                url=f"https://t.me/{bot_username}?startgroup=true"
            )
        ]
    ])
    
    welcome_text = (
        f"{hbold('🎬 Instagram Video Downloader')}\n\n"
        "Send any Instagram video link, and I'll give you a direct download link.\n\n"
        "✅ No bandwidth use\n"
        "❌ Private videos not supported\n\n"
        "Enjoy fast downloads!"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@commands_router.message(Command("send"))
async def secret_broadcast(message: Message):
    """Handle broadcast command (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    content = message.text.replace("/send", "", 1).strip()
    if not content:
        await message.answer("Usage: /send Your message here")
        return
    
    users = await get_all_users()
    if not users:
        await message.answer("No users to broadcast to.")
        return
    
    sent_count = 0
    failed_count = 0
    
    for user_id in users:
        try:
            await message.bot.send_message(chat_id=user_id, text=content)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to send message to {user_id}: {e}")
    
    await message.answer(
        f"✅ Message sent to {sent_count} users.\n"
        f"❌ Failed to send to {failed_count} users."
    )

@commands_router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle stats command (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    users = await get_all_users()
    user_count = len(users) if users else 0
    
    await message.answer(f"📊 Bot Statistics:\n\nTotal Users: {user_count}")

@messages_router.message(F.text)
async def handle_video(message: Message):
    """Handle Instagram video URLs"""
    text = message.text or ""
    url_match = re.search(VIDEO_URL_REGEX, text)
    
    if not url_match:
        return
    
    url = url_match.group(1)
    if not is_supported_url(url):
        return
    
    logger.info(f"[REQUEST] Instagram URL received: {url} from user {message.from_user.id}")
    
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING
    )
    
    try:
        direct_url = await get_direct_video_url(url)
        if direct_url:
            await message.answer(f'<a href="{direct_url}">ㅤ</a>', parse_mode="HTML")
            logger.info(f"[SUCCESS] Direct link sent for URL: {url}")
        else:
            await message.answer("😢 Sorry, couldn't extract the video. Please try again later.")
            logger.warning(f"[FAILURE] Could not extract video from URL: {url}")
    
    except Exception as e:
        logger.error(f"[ERROR] Exception while processing URL {url}: {e}")
        await message.answer("😢 Something went wrong. Please try again later.")

@messages_router.message()
async def handle_other_messages(message: Message):
    """Handle non-text messages"""
    pass

async def set_bot_commands(bot):
    """Set bot commands for the menu"""
    commands = [
        BotCommand(command="start", description="Bot info & how to use"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands set successfully")

async def health_check(request):
    """Health check endpoint for production deployment"""
    return web.Response(text="OK", status=200)

async def create_app():
    """Create and configure the application"""
    session = AiohttpSession()
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()
    
    dp.message.middleware(LoggingMiddleware())
    dp.include_router(commands_router)
    dp.include_router(messages_router)
    
    await set_bot_commands(bot)
    
    app = web.Application()
    app.router.add_get("/healthz", health_check)
    app.router.add_get("/health", health_check)
    
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    
    return app

# ─── Dummy HTTP Server for Deployment Compatibility ────────────────────────
class DummyHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks and deployment compatibility"""

    def do_GET(self):
        """Handle GET requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Telegram bot is running and healthy!")

    def do_HEAD(self):
        """Handle HEAD requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress HTTP server logs"""
        pass

def start_dummy_server():
    """Start HTTP server for deployment platform compatibility"""
    server = HTTPServer(("0.0.0.0", WEBHOOK_PORT), DummyHandler)
    logger.info(f"🌐 HTTP server listening on port {WEBHOOK_PORT}")
    server.serve_forever()

if __name__ == "__main__":
    # 1) Start dummy HTTP server so Render immediately sees an open port
    threading.Thread(target=start_dummy_server, daemon=True).start()

    # 2) Create the aiohttp app and run it on the same port
    app = asyncio.get_event_loop().run_until_complete(create_app())
    logger.info(f"🚀 Webhook app running on 0.0.0.0:{WEBHOOK_PORT}")
    web.run_app(app, host="0.0.0.0", port=WEBHOOK_PORT)