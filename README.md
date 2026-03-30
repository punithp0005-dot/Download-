# ViralCutz - Telegram Video Bot

Automated video clip downloader and editor bot for Telegram with AI-powered viral moment detection.

## Features

- 🎥 Download clips from YouTube, Twitch, Instagram, TikTok, and more
- 🤖 AI-powered viral moment detection using NVIDIA API
- 🎨 Automatic video editing with emotion-based styles
- 🎤 Voice narration with text-to-speech
- 📱 Optimized for Instagram/TikTok format (1:1 aspect ratio)

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `TELEGRAM_TOKEN` - Your Telegram bot token from [@BotFather](https://t.me/botfather)
- `CHAT_ID` - Your Telegram chat ID

Optional:
- `NVIDIA_KEY` - NVIDIA API key for AI analysis (get from [build.nvidia.com](https://build.nvidia.com/))

### 2. Dependencies

Install required packages:
```bash
pip install yt-dlp edge-tts requests
```

System requirements:
- Python 3.11+
- ffmpeg
- yt-dlp

### 3. Docker Deployment (Recommended)

For 24/7 operation on free cloud platforms:

```bash
docker build -t viralcutz-bot -f Dockerfile.txt .
docker run -e TELEGRAM_TOKEN=xxx -e CHAT_ID=xxx -e NVIDIA_KEY=xxx viralcutz-bot
```

## Performance Improvements

This version includes significant performance and security improvements:

### Security
- ✅ Removed hardcoded credentials
- ✅ Environment variable enforcement
- ✅ Input validation for URLs

### Performance
- ✅ ThreadPoolExecutor for bounded concurrency (max 5 workers)
- ✅ Optimized string operations with translation tables
- ✅ Efficient multipart form data building
- ✅ Compiled regex patterns
- ✅ Reduced file system operations

### Reliability
- ✅ Subprocess timeouts (prevents hanging)
- ✅ Proper error handling with specific exceptions
- ✅ Guaranteed cleanup with try-finally blocks
- ✅ Better error messages for users

## Usage

Send `/start` in Telegram to see all available commands.

## Free 24/7 Deployment Options

Deploy on free cloud platforms:
- Railway.app (500 hours/month free)
- Render.com (750 hours/month free)
- Fly.io (Free tier available)

## Security Notes

⚠️ **IMPORTANT**: Never commit `.env` file or expose API keys in your code!

The bot now enforces environment variables and will not start without proper configuration.