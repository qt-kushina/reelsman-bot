# 🎬 Instagram Video Downloader Bot  
[![Telegram Bot](https://img.shields.io/badge/Launch%20Bot-@YourInstaDLBot-2CA5E0?logo=telegram&style=for-the-badge)](https://t.me/YourInstaDLBot)

> **Fast. Lightweight. Hassle-free.**  
> Send any public Instagram video link and get a direct download URL—no re-uploads, no bandwidth drain.

---

## ✨ Key Features

- 📥 **Direct Links** — Extracts best-quality video URL up to 720p  
- 🔄 **Retry Logic** — Automatic re-attempts on first failure  
- 🔒 **No Downloads** — Doesn’t consume your storage or bandwidth  
- 🤖 **Silent Mode** — Only responds when you send a valid link  
- 📊 **Usage Analytics** — Logs successes and failures for easy debugging  

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+  
- **Framework:** [aiogram](https://docs.aiogram.dev/) (async Telegram bot)  
- **Downloader:** [yt-dlp](https://github.com/yt-dlp/yt-dlp)  
- **Hosting:** Railway (or any Python-friendly host)  
- **Logging:** Python’s built-in `logging` module  

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-username/instadl-bot.git
cd instadl-bot

# 2. Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Telegram Bot Token
export BOT_TOKEN="123456789:ABCDEF-your-telegram-bot-token"

# 5. Run the bot
python bot.py