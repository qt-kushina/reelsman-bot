# 🚀 Instagram Video Link Extractor Bot

A lightweight, lightning-fast Telegram bot that extracts **direct download links** from public Instagram videos — powered by Python & aiogram. No ads, no fluff — just clean links.

---

## ✨ Features

- ✅ Supports public Instagram video links (Reels, Posts, etc.)
- ⚡️ Fast & bandwidth-efficient (only ~10–50KB per request)
- 🧠 Smart filtering — ignores non-Instagram or unsupported links
- 🤖 Telegram-native UX with inline buttons & auto-replies
- 🔐 No data stored — completely stateless

---

## 📌 Supported Platforms

Only links from:

- `instagram.com`  
*(Reels, posts, videos — public content only)*

---

## 🛠 Tech Stack

- **Python 3.12+**
- **[aiogram v3](https://docs.aiogram.dev/)**
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
- **Railway** (for cloud deployment)

---

## 🚧 Environment Setup

> ⚙️ You only need one environment variable to get started.

| Variable   | Description              |
|------------|--------------------------|
| `BOT_TOKEN` | Your Telegram bot token from [@BotFather](https://t.me/BotFather) |

Set this in your [Railway](https://railway.app) project under **Variables**.

---

## 🚀 Deploy to Railway (1-click setup)

1. **Fork** this repo
2. Head to [Railway](https://railway.app)
3. Click **“New Project” → “Deploy from GitHub Repo”**
4. Set the `BOT_TOKEN` in the **Environment Variables** tab
5. You're done! Your bot is now live.

---

## ⚙️ Local Development

### Install Requirements

```bash
pip install -r requirements.txt