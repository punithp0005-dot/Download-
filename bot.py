import os, json, subprocess, urllib.request, re, time, threading

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8616029065:AAGFEklmW_3ZSLmVGEDOr0JwnunkScRRsxc")
CHAT_ID = os.environ.get("CHAT_ID", "8095220898")
OUT = "/tmp/downloads"
os.makedirs(OUT, exist_ok=True)
TG = "https://api.telegram.org/bot" + TELEGRAM_TOKEN

SUPPORTED = [
    "youtube.com", "youtu.be", "twitch.tv",
    "instagram.com", "facebook.com", "fb.com",
    "tiktok.com", "twitter.com", "x.com",
    "reddit.com", "vimeo.com", "dailymotion.com",
    "streamable.com", "clips.twitch.tv"
]

def tg(method, data):
    url = TG + "/" + method
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print("TG error:", e)
        return {}

def send(chat_id, text):
    tg("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def send_video(chat_id, path, caption=""):
    boundary = "VCB123"
    with open(path, "rb") as f:
        vid = f.read()
    body = (
        ("--"+boundary+"\r\n").encode() +
        ("Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n").encode() +
        (str(chat_id)+"\r\n").encode() +
        ("--"+boundary+"\r\n").encode() +
        ("Content-Disposition: form-data; name=\"caption\"\r\n\r\n").encode() +
        (caption[:900]+"\r\n").encode() +
        ("--"+boundary+"\r\n").encode() +
        ("Content-Disposition: form-data; name=\"video\"; filename=\"video.mp4\"\r\n").encode() +
        ("Content-Type: video/mp4\r\n\r\n").encode() +
        vid +
        ("\r\n--"+boundary+"--\r\n").encode()
    )
    req = urllib.request.Request(TG+"/sendVideo", data=body,
          headers={"Content-Type": "multipart/form-data; boundary="+boundary})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print("Video send error:", e)

def send_audio(chat_id, path, caption=""):
    boundary = "VCB456"
    with open(path, "rb") as f:
        aud = f.read()
    body = (
        ("--"+boundary+"\r\n").encode() +
        ("Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n").encode() +
        (str(chat_id)+"\r\n").encode() +
        ("--"+boundary+"\r\n").encode() +
        ("Content-Disposition: form-data; name=\"caption\"\r\n\r\n").encode() +
        (caption[:900]+"\r\n").encode() +
        ("--"+boundary+"\r\n").encode() +
        ("Content-Disposition: form-data; name=\"audio\"; filename=\"audio.mp3\"\r\n").encode() +
        ("Content-Type: audio/mpeg\r\n\r\n").encode() +
        aud +
        ("\r\n--"+boundary+"--\r\n").encode()
    )
    req = urllib.request.Request(TG+"/sendAudio", data=body,
          headers={"Content-Type": "multipart/form-data; boundary="+boundary})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print("Audio send error:", e)

def get_info(url):
    cmd = ["yt-dlp", "--dump-json", "--no-playlist", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except:
        return None

def download_video(chat_id, url, quality="1080"):
    ts = str(int(time.time()))
    out = os.path.join(OUT, "video_"+ts+".mp4")

    send(chat_id, "📡 Getting video info...")
    info = get_info(url)
    if info:
        title = info.get("title","Unknown")[:50]
        duration = info.get("duration", 0)
        uploader = info.get("uploader","Unknown")
        dur_str = str(int(duration//60))+"m "+str(int(duration%60))+"s" if duration else "?"
        send(chat_id, "📹 <b>"+title+"</b>\n👤 "+uploader+"\n⏱ "+dur_str+"\n\n📥 Downloading in "+quality+"p...")
    else:
        send(chat_id, "📥 Downloading...")

    # Quality format selection
    if quality == "1440":
        fmt = "bestvideo[height<=1440]+bestaudio/bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440]/best"
    elif quality == "1080":
        fmt = "bestvideo[height<=1080]+bestaudio/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best"
    elif quality == "720":
        fmt = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
    elif quality == "480":
        fmt = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
    else:
        fmt = "best"

    cmd = [
        "yt-dlp",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "-o", out,
        "--no-playlist",
        "--retries", "3",
        url
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)

    if not os.path.exists(out):
        # Fallback to best available
        cmd2 = ["yt-dlp", "-f", "best", "--merge-output-format", "mp4", "-o", out, "--no-playlist", url]
        subprocess.run(cmd2, capture_output=True)

    if os.path.exists(out) and os.path.getsize(out) > 10000:
        size = os.path.getsize(out) / (1024*1024)
        caption = "✅ "+quality+"p | "+str(round(size,1))+"MB\n@_ViralCutz"
        send(chat_id, "📤 Sending video...")
        send_video(chat_id, out, caption)
        os.remove(out)
        send(chat_id, "✅ Done! Video sent in "+quality+"p 🎬")
    else:
        send(chat_id, "❌ Download failed! Try different quality or check URL.")

def download_clip(chat_id, url, start, end, quality="1080"):
    ts = str(int(time.time()))
    out = os.path.join(OUT, "clip_"+ts+".mp4")

    def fix_ts(ts):
        ts = ts.strip()
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = parts
            if int(h) == 0:
                return str(int(m))+":"+s
        return ts

    start = fix_ts(start)
    end = fix_ts(end)

    send(chat_id, "📥 Downloading clip "+start+" → "+end+" in "+quality+"p...")

    fmt = "bestvideo[height<="+quality+"]+bestaudio/best[height<="+quality+"]/best"
    cmd = [
        "yt-dlp",
        "--download-sections", "*"+start+"-"+end,
        "-f", fmt,
        "--merge-output-format", "mp4",
        "-o", out,
        "--no-playlist",
        "--retries", "3",
        url
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(out) and os.path.getsize(out) > 10000:
        size = os.path.getsize(out) / (1024*1024)
        caption = "✅ Clip "+start+"-"+end+" | "+quality+"p | "+str(round(size,1))+"MB\n@_ViralCutz"
        send(chat_id, "📤 Sending clip...")
        send_video(chat_id, out, caption)
        os.remove(out)
        send(chat_id, "✅ Clip sent! 🎬")
    else:
        send(chat_id, "❌ Clip download failed!")

def download_audio(chat_id, url):
    ts = str(int(time.time()))
    out = os.path.join(OUT, "audio_"+ts+".mp3")

    send(chat_id, "🎵 Downloading audio...")
    cmd = [
        "yt-dlp",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", out,
        "--no-playlist",
        url
    ]
    subprocess.run(cmd, capture_output=True)

    if os.path.exists(out) and os.path.getsize(out) > 1000:
        send(chat_id, "📤 Sending audio...")
        send_audio(chat_id, out, "🎵 Audio | @_ViralCutz")
        os.remove(out)
        send(chat_id, "✅ Audio sent! 🎵")
    else:
        send(chat_id, "❌ Audio download failed!")

def handle(message):
    chat_id = str(message.get("chat",{}).get("id",""))
    text = message.get("text","").strip()
    if not text or not chat_id:
        return
    print("Msg:", chat_id, text[:80])

    if text.startswith("/start"):
        send(chat_id,
            "🎬 <b>ViralCutz Downloader Bot</b>\n\n"
            "Download from ANY platform in high quality!\n\n"
            "<b>Supported:</b>\n"
            "YouTube • Twitch • Instagram\n"
            "Facebook • TikTok • Twitter/X\n"
            "Reddit • Vimeo • And more!\n\n"
            "<b>Commands:</b>\n"
            "/dl [url] — Download full video 1080p\n"
            "/dl1440 [url] — Download in 1440p\n"
            "/dl720 [url] — Download in 720p\n"
            "/dl480 [url] — Download in 480p\n"
            "/audio [url] — Download audio MP3\n"
            "/clip [url] [start] [end] — Download clip\n\n"
            "<b>Example:</b>\n"
            "<code>/clip https://youtu.be/xxx 5:00 5:50</code>\n\n"
            "Or just paste any link for 1080p! 🚀")
        return

    # Just paste a link - auto download 1080p
    for site in SUPPORTED:
        if site in text:
            url = text.split()[0]
            threading.Thread(target=download_video, args=(chat_id, url, "1080"), daemon=True).start()
            return

    # Commands
    if text.startswith("/dl1440 "):
        url = text.replace("/dl1440 ","").strip()
        threading.Thread(target=download_video, args=(chat_id, url, "1440"), daemon=True).start()
        return

    if text.startswith("/dl720 "):
        url = text.replace("/dl720 ","").strip()
        threading.Thread(target=download_video, args=(chat_id, url, "720"), daemon=True).start()
        return

    if text.startswith("/dl480 "):
        url = text.replace("/dl480 ","").strip()
        threading.Thread(target=download_video, args=(chat_id, url, "480"), daemon=True).start()
        return

    if text.startswith("/dl "):
        url = text.replace("/dl ","").strip()
        threading.Thread(target=download_video, args=(chat_id, url, "1080"), daemon=True).start()
        return

    if text.startswith("/audio "):
        url = text.replace("/audio ","").strip()
        threading.Thread(target=download_audio, args=(chat_id, url), daemon=True).start()
        return

    if text.startswith("/clip "):
        parts = text.split()
        if len(parts) >= 4:
            url = parts[1]
            start = parts[2]
            end = parts[3]
            threading.Thread(target=download_clip, args=(chat_id, url, start, end, "1080"), daemon=True).start()
        else:
            send(chat_id, "Usage: /clip [url] [start] [end]\nExample: /clip https://youtu.be/xxx 5:00 5:50")
        return

    send(chat_id, "Send /start to see all commands!\nOr just paste any video link! 🎬")

def get_updates(offset=0):
    url = TG+"/getUpdates?offset="+str(offset)+"&timeout=30"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=35) as r:
            return json.loads(r.read().decode())
    except:
        return {"result":[]}

def main():
    print("ViralCutz Downloader Bot starting...")
    tg("sendMessage",{"chat_id":CHAT_ID,"text":"🚀 <b>ViralCutz Downloader Bot is online!</b>\nSend /start to see all commands!","parse_mode":"HTML"})
    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            for u in updates.get("result",[]):
                offset = u["update_id"]+1
                msg = u.get("message",{})
                if msg:
                    threading.Thread(target=handle, args=(msg,), daemon=True).start()
        except Exception as e:
            print("Loop error:", str(e)[:100])
            time.sleep(5)

if __name__ == "__main__":
    main()
