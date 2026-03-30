import os, json, subprocess, urllib.request, re, time, threading
from concurrent.futures import ThreadPoolExecutor
import io

# Enforce required environment variables - no hardcoded defaults for security
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
NVIDIA_KEY = os.environ.get("NVIDIA_KEY")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN and CHAT_ID environment variables are required")
if not NVIDIA_KEY:
    print("Warning: NVIDIA_KEY not set - AI analysis will not work")
WATERMARK = "@_ViralCutz"
OUT = "/tmp/clips"
os.makedirs(OUT, exist_ok=True)
TG = "https://api.telegram.org/bot" + TELEGRAM_TOKEN

# Thread pool for managing concurrent video processing
MAX_WORKERS = 5  # Limit concurrent video processing to prevent resource exhaustion
thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Compiled regex for efficient clip splitting
CLIP_SPLIT_PATTERN = re.compile(r"(?=URL:)")

FX = {
    "hype":      {"eq":"contrast=1.22:saturation=1.35:brightness=0.03","tc":"0x00ff44","bc":"0x006600@0.80","gl":True,"af":"bass=g=10,volume=1.5"},
    "funny":     {"eq":"contrast=1.15:saturation=1.45:brightness=0.04","tc":"0xffff00","bc":"0x666600@0.80","gl":True,"af":"bass=g=6,volume=1.35"},
    "angry":     {"eq":"contrast=1.28:saturation=1.20:brightness=0.01","tc":"0xff3333","bc":"0x660000@0.85","gl":True,"af":"bass=g=12,volume=1.55"},
    "emotional": {"eq":"contrast=1.08:saturation=0.90:brightness=0.02","tc":"0x00cfff","bc":"0x003366@0.75","gl":False,"af":"bass=g=3,volume=1.1"},
    "shocked":   {"eq":"contrast=1.24:saturation=1.10:brightness=0.02","tc":"0xffffff","bc":"0x333333@0.80","gl":True,"af":"bass=g=7,volume=1.4"},
    "happy":     {"eq":"contrast=1.12:saturation=1.40:brightness=0.05","tc":"0x00ff88","bc":"0x004400@0.75","gl":False,"af":"bass=g=5,volume=1.3"},
}

SUPPORTED = ["youtube.com","youtu.be","twitch.tv","instagram.com","facebook.com","tiktok.com","twitter.com","x.com","reddit.com","vimeo.com"]

def tg(method, data):
    url = TG + "/" + method
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.URLError as e:
        print(f"TG network error ({method}):", str(e)[:100])
        return {}
    except json.JSONDecodeError as e:
        print(f"TG JSON error ({method}):", str(e)[:100])
        return {}
    except Exception as e:
        print(f"TG unexpected error ({method}):", str(e)[:100])
        return {}

def send(chat_id, text):
    tg("sendMessage", {"chat_id":chat_id, "text":text, "parse_mode":"HTML"})

def send_video(chat_id, path, caption=""):
    boundary = "VCB123"
    try:
        with open(path, "rb") as f:
            vid = f.read()
    except IOError as e:
        print(f"Error reading video file {path}: {e}")
        return None

    # Optimized multipart form data building using BytesIO
    body_parts = [
        b"--" + boundary.encode() + b"\r\n",
        b"Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n",
        str(chat_id).encode() + b"\r\n",
        b"--" + boundary.encode() + b"\r\n",
        b"Content-Disposition: form-data; name=\"caption\"\r\n\r\n",
        caption[:900].encode() + b"\r\n",
        b"--" + boundary.encode() + b"\r\n",
        b"Content-Disposition: form-data; name=\"video\"; filename=\"clip.mp4\"\r\n",
        b"Content-Type: video/mp4\r\n\r\n",
        vid,
        b"\r\n--" + boundary.encode() + b"--\r\n"
    ]
    body = b"".join(body_parts)

    req = urllib.request.Request(TG+"/sendVideo", data=body,
          headers={"Content-Type":"multipart/form-data; boundary="+boundary})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.URLError as e:
        print(f"Video upload network error: {str(e)[:100]}")
        return None
    except Exception as e:
        print(f"Video upload error: {str(e)[:100]}")
        return None

def make_voice(text, out_path):
    try:
        import edge_tts, asyncio
        async def gen():
            c = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate="+5%", volume="+10%")
            await c.save(out_path)
        asyncio.run(gen())
        return os.path.exists(out_path)
    except Exception as e:
        print("Voice error:", e)
        return False

def ask_nvidia(prompt):
    if not NVIDIA_KEY:
        print("NVIDIA_KEY not configured")
        return None

    headers = {
        "Authorization": "Bearer " + NVIDIA_KEY,
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role":"user","content":prompt}],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 2048,
        "stream": False
    }).encode()
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=data, headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read().decode())
            return res["choices"][0]["message"]["content"]
    except urllib.error.URLError as e:
        print(f"Nvidia network error: {str(e)[:200]}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Nvidia response parsing error: {str(e)[:200]}")
        return None
    except Exception as e:
        print(f"Nvidia unexpected error: {str(e)[:200]}")
        return None

def fix_ts(ts):
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        if int(h) == 0:
            return str(int(m))+":"+s
    return ts

# Optimized escape function using translation table for O(n) complexity
_escape_table = str.maketrans({
    '\\': '\\\\',
    "'": "\\'",
    ':': '\\:',
    ',': '\\,',
    '[': '\\[',
    ']': '\\]'
})

def e(t):
    """Escape special characters for ffmpeg drawtext filter"""
    return str(t).translate(_escape_table)

def download_only(chat_id, url, start, end, quality="1080"):
    ts = str(int(time.time()))
    out = os.path.join(OUT, "clip_"+ts+".mp4")
    start = fix_ts(start)
    end = fix_ts(end)
    send(chat_id, "📥 Downloading "+start+" → "+end+" in "+quality+"p...")
    fmt = "bestvideo[height<="+quality+"]+bestaudio/best[height<="+quality+"]/best"
    cmd = ["yt-dlp","--download-sections","*"+start+"-"+end,
           "-f",fmt,"--merge-output-format","mp4",
           "-o",out,"--no-playlist","--retries","3",url]

    try:
        subprocess.run(cmd, capture_output=True, timeout=600)  # 10 min timeout

        # Optimized file check - single stat call
        try:
            file_size = os.path.getsize(out)
            if file_size < 10000:
                raise ValueError("File too small")
        except (OSError, ValueError):
            # Retry with simpler format
            cmd2 = ["yt-dlp","--download-sections","*"+start+"-"+end,
                    "-f","best","--merge-output-format","mp4",
                    "-o",out,"--no-playlist",url]
            subprocess.run(cmd2, capture_output=True, timeout=600)
            file_size = os.path.getsize(out)

        if file_size > 10000:
            size_mb = round(file_size/(1024*1024), 1)
            send_video(chat_id, out, "✅ "+quality+"p | "+str(size_mb)+"MB | "+WATERMARK)
            send(chat_id, "✅ Clip sent! Ready to edit in IG Edits! 🎬")
        else:
            send(chat_id, "❌ Download failed! File too small.")
    except subprocess.TimeoutExpired:
        send(chat_id, "❌ Download timeout! Video might be too long or connection is slow.")
    except OSError as e:
        send(chat_id, f"❌ Download failed! {str(e)[:50]}")
    finally:
        # Cleanup in finally block to ensure it happens
        if os.path.exists(out):
            try:
                os.remove(out)
            except OSError:
                pass

def download_full(chat_id, url, quality="1080"):
    ts = str(int(time.time()))
    out = os.path.join(OUT, "full_"+ts+".mp4")
    send(chat_id, "📥 Downloading full video in "+quality+"p...")
    fmt = "bestvideo[height<="+quality+"]+bestaudio/best[height<="+quality+"]/best"
    cmd = ["yt-dlp","-f",fmt,"--merge-output-format","mp4",
           "-o",out,"--no-playlist","--retries","3",url]

    try:
        subprocess.run(cmd, capture_output=True, timeout=1200)  # 20 min timeout for full videos

        # Optimized file check
        try:
            file_size = os.path.getsize(out)
            if file_size < 10000:
                raise ValueError("File too small")
        except (OSError, ValueError):
            cmd2 = ["yt-dlp","-f","best","--merge-output-format","mp4",
                    "-o",out,"--no-playlist",url]
            subprocess.run(cmd2, capture_output=True, timeout=1200)
            file_size = os.path.getsize(out)

        if file_size > 10000:
            size_mb = round(file_size/(1024*1024), 1)
            send_video(chat_id, out, "✅ "+quality+"p | "+str(size_mb)+"MB | "+WATERMARK)
            send(chat_id, "✅ Video sent! 🎬")
        else:
            send(chat_id, "❌ Download failed! File too small.")
    except subprocess.TimeoutExpired:
        send(chat_id, "❌ Download timeout! Video is too large or connection is slow.")
    except OSError as e:
        send(chat_id, f"❌ Download failed! {str(e)[:50]}")
    finally:
        if os.path.exists(out):
            try:
                os.remove(out)
            except OSError:
                pass

def edit_clip(chat_id, url, start, end, emotion, hook, line1, line2, action, caption, num):
    ts = str(int(time.time()))
    raw   = os.path.join(OUT, "raw_"+ts+".mp4")
    sq    = os.path.join(OUT, "sq_"+ts+".mp4")
    voice = os.path.join(OUT, "voice_"+ts+".mp3")
    final = os.path.join(OUT, "final_"+ts+".mp4")

    try:
        start = fix_ts(start)
        end   = fix_ts(end)

        send(chat_id, "📥 Downloading clip "+str(num)+"... "+start+" → "+end)

        cmd = ["yt-dlp","--download-sections","*"+start+"-"+end,
               "-f","bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
               "--merge-output-format","mp4","-o",raw,"--no-playlist","--retries","3",url]
        subprocess.run(cmd, capture_output=True, timeout=600)

        # Optimized file check
        try:
            file_size = os.path.getsize(raw)
            if file_size < 10000:
                raise ValueError("File too small")
        except (OSError, ValueError):
            cmd2 = ["yt-dlp","--download-sections","*"+start+"-"+end,
                    "-f","best","--merge-output-format","mp4","-o",raw,"--no-playlist",url]
            subprocess.run(cmd2, capture_output=True, timeout=600)
            file_size = os.path.getsize(raw)

        if file_size < 10000:
            send(chat_id, "❌ Download failed clip "+str(num))
            return

        send(chat_id, "🎤 Adding voice intro...")
        voice_text = hook+". "+line1+" "+line2+". Watch what happens!"
        has_voice = make_voice(voice_text, voice)

        send(chat_id, "🎨 Editing in "+emotion.upper()+" style...")

        fx = FX.get(emotion, FX["hype"])
        tc = fx["tc"]
        bc = fx["bc"]

        # Step 1: Make 1:1 blur background
        r1 = subprocess.run([
            "ffmpeg","-y","-i",raw,
            "-filter_complex",
            "[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,boxblur=20:20[bg];"
            "[0:v]scale=810:810:force_original_aspect_ratio=decrease,pad=810:810:(ow-iw)/2:(oh-ih)/2[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]",
            "-map","[v]","-map","0:a",
            "-c:v","libx264","-preset","fast","-crf","16",
            "-c:a","aac","-b:a","192k", sq
        ], capture_output=True, timeout=300)

        src = sq if r1.returncode == 0 and os.path.exists(sq) else raw

        # Step 2: Add subtitles - optimized filter building
        h_e   = e(hook)
        l1_e  = e(line1)
        l2_e  = e(line2)
        act_e = e(action)
        wm_e  = e(WATERMARK)

        # Build filter list and join for efficiency
        vf_parts = [
            fx["eq"],
            "drawtext=text='"+h_e+"':fontcolor=white:fontsize=55:font=Sans:"
            "x=(w-text_w)/2:y=50:shadowcolor=black:shadowx=2:shadowy=2:"
            "box=1:boxcolor=black@0.6:boxborderw=8:enable='between(t,0,3)'",
            "drawtext=text='"+l1_e+"':fontcolor=white:fontsize=58:font=Sans:"
            "x=(w-text_w)/2:y=h-200:shadowcolor=black:shadowx=2:shadowy=2:"
            "enable='between(t,3,15)'",
            "drawtext=text='"+l2_e+"':fontcolor="+tc+":fontsize=62:font=Sans:"
            "x=(w-text_w)/2:y=h-130:shadowcolor=black:shadowx=3:shadowy=3:"
            "box=1:boxcolor="+bc+":boxborderw=10:enable='between(t,15,32)'",
            "drawtext=text='"+act_e+"':fontcolor="+tc+":fontsize=58:font=Sans:"
            "x=(w-text_w)/2:y=h-160:shadowcolor=black:shadowx=3:shadowy=3:"
            "box=1:boxcolor="+bc+":boxborderw=10:enable='between(t,32,55)'",
            "drawtext=text='"+wm_e+"':fontcolor=white@0.15:fontsize=20:font=Sans:"
            "x=(w-text_w)/2:y=h-30"
        ]

        if fx["gl"]:
            vf_parts.append("rgbashift=rh=3:rv=0:bh=-3:bv=0:enable='between(t,14.9,15.1)'")
            vf_parts.append("rgbashift=rh=4:rv=1:bh=-4:bv=-1:enable='between(t,31.9,32.1)'")

        vf = ",".join(vf_parts)

        if has_voice and os.path.exists(voice):
            r2 = subprocess.run([
                "ffmpeg","-y","-i",src,"-i",voice,
                "-filter_complex",
                "[0:v]"+vf+"[v];"
                "[1:a]volume=2.0[va];"
                "[0:a]"+fx["af"]+"[oa];"
                "[va][oa]amix=inputs=2:duration=shortest:weights=3 1[a]",
                "-map","[v]","-map","[a]",
                "-c:v","libx264","-preset","fast","-crf","16",
                "-b:v","4000k","-c:a","aac","-b:a","192k",final
            ], capture_output=True, text=True, timeout=600)
        else:
            r2 = subprocess.run([
                "ffmpeg","-y","-i",src,
                "-vf",vf,"-af",fx["af"],
                "-c:v","libx264","-preset","fast","-crf","16",
                "-b:v","4000k","-c:a","aac","-b:a","192k",final
            ], capture_output=True, text=True, timeout=600)

        print("Edit rc:", r2.returncode)
        if r2.returncode != 0:
            print("Edit err:", r2.stderr[-300:] if r2.stderr else "no stderr")
            send(chat_id, "⚠️ Edit had issues, trying fallback for clip "+str(num))
            # Fallback - just color grade
            subprocess.run([
                "ffmpeg","-y","-i",src,
                "-vf",fx["eq"],"-af",fx["af"],
                "-c:v","libx264","-preset","fast","-crf","16",
                "-c:a","aac",final
            ], capture_output=True, timeout=300)

        # Check final result
        try:
            final_size = os.path.getsize(final)
            if final_size > 10000:
                send_video(chat_id, final, caption)
                send(chat_id, "✅ <b>Clip "+str(num)+" done!</b>\n\n📝 Caption:\n"+caption)
            else:
                send(chat_id, "❌ Edit failed clip "+str(num)+" (file too small)")
        except OSError:
            send(chat_id, "❌ Edit failed clip "+str(num)+" (file not created)")

    except subprocess.TimeoutExpired:
        send(chat_id, "❌ Timeout processing clip "+str(num))
    except Exception as e:
        send(chat_id, f"❌ Error clip {num}: {str(e)[:50]}")
    finally:
        # Guaranteed cleanup of all temporary files
        for f in [raw, sq, voice, final]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

def parse_command(text):
    """Parse clip command data with validation"""
    data = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("URL:"): data["url"] = line.replace("URL:","").strip()
        elif line.startswith("START:"): data["start"] = line.replace("START:","").strip()
        elif line.startswith("END:"): data["end"] = line.replace("END:","").strip()
        elif line.startswith("EMOTION:"): data["emotion"] = line.replace("EMOTION:","").strip().lower()
        elif line.startswith("HOOK:"): data["hook"] = line.replace("HOOK:","").strip()
        elif line.startswith("LINE1:"): data["line1"] = line.replace("LINE1:","").strip()
        elif line.startswith("LINE2:"): data["line2"] = line.replace("LINE2:","").strip()
        elif line.startswith("ACTION:"): data["action"] = line.replace("ACTION:","").strip()
        elif line.startswith("CAPTION:"): data["caption"] = line.replace("CAPTION:","").strip()
        elif line.startswith("NUM:"): data["num"] = line.replace("NUM:","").strip()
    return data

def validate_url(url):
    """Validate if URL is from supported platforms"""
    for site in SUPPORTED:
        if site in url:
            return True
    return False

def analyze_video(chat_id, url):
    # Validate URL first
    if not validate_url(url):
        send(chat_id, "❌ Unsupported platform! Supported: YouTube, Twitch, Instagram, TikTok, Twitter, Reddit, Vimeo")
        return

    send(chat_id, "📡 Getting video info...")
    cmd = ["yt-dlp","--dump-json","--no-playlist",url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        send(chat_id, "❌ Timeout getting video info")
        return

    title = "Unknown"; channel = "Unknown"; duration = 0
    try:
        info = json.loads(r.stdout)
        title = info.get("title","Unknown")
        channel = info.get("uploader","Unknown")
        duration = info.get("duration",0)
        send(chat_id, "✅ <b>"+title+"</b>\nChannel: "+channel)
    except json.JSONDecodeError:
        send(chat_id, "⚠️ Could not parse video info, continuing anyway...")

    send(chat_id, "🤖 AI finding ALL viral moments...")
    dur_str = str(int(duration//60))+"m "+str(int(duration%60))+"s" if duration else "unknown"
    prompt = (
        "You are a viral clip expert.\nAnalyze this video and find ALL best viral moments.\n\n"
        "Title: "+title+"\nChannel: "+channel+"\nDuration: "+dur_str+"\nURL: "+url+"\n\n"
        "For EVERY viral moment provide EXACTLY:\n\n"
        "URL: "+url+"\nSTART: MM:SS\nEND: MM:SS\n"
        "EMOTION: hype/funny/angry/emotional/shocked/happy\n"
        "HOOK: HOOK TEXT ALL CAPS MAX 6 WORDS\n"
        "LINE1: WHITE TEXT MAX 5 WORDS ALL CAPS\n"
        "LINE2: COLORED TEXT MAX 5 WORDS ALL CAPS\n"
        "ACTION: *ACTION TEXT ALL CAPS*\n"
        "CAPTION: Instagram caption with emojis and hashtags\n"
        "NUM: 1\n\nList ALL highlights. Be specific with timestamps."
    )
    response = ask_nvidia(prompt)
    if not response:
        send(chat_id, "❌ AI failed. Use /prompt to get Gemini prompt!"); return

    # Use compiled regex pattern for efficiency
    clips_text = CLIP_SPLIT_PATTERN.split(response)
    clips_text = [c for c in clips_text if "URL:" in c and "START:" in c]
    if not clips_text:
        send(chat_id, "❌ No clips found. Try /prompt!"); return

    send(chat_id, "🎬 Found <b>"+str(len(clips_text))+" viral moments!</b>\nProcessing...")
    for i, ct in enumerate(clips_text):
        d = parse_command(ct)
        if d.get("url") and d.get("start") and d.get("end"):
            # Use thread pool instead of unbounded thread creation
            thread_pool.submit(
                edit_clip, chat_id, d["url"], d["start"], d["end"],
                d.get("emotion","hype"), d.get("hook","WATCH THIS"),
                d.get("line1","CHECK THIS"), d.get("line2","RIGHT NOW"),
                d.get("action","*INCREDIBLE*"),
                d.get("caption","Viral moment! #viral #fyp"),
                d.get("num",str(i+1))
            )
            time.sleep(3)

def handle(message):
    chat_id = str(message.get("chat",{}).get("id",""))
    text = message.get("text","").strip()
    if not text or not chat_id: return
    print("Msg:", chat_id, text[:80])

    if text.startswith("/start"):
        send(chat_id,
            "🎬 <b>ViralCutz AI Bot</b>\n\n"
            "<b>Commands:</b>\n\n"
            "🔗 Paste any YouTube/Twitch link → AI finds + edits clips!\n\n"
            "/clip [url] [start] [end] → Download clip only\n"
            "/dl [url] → Download full video 1080p\n"
            "/dl1440 [url] → Download 1440p\n"
            "/dl720 [url] → Download 720p\n"
            "/prompt → Get Gemini prompt for manual use\n\n"
            "<b>Example:</b>\n"
            "<code>/clip https://youtu.be/xxx 5:00 5:50</code>")
        return

    if text.startswith("/prompt"):
        send(chat_id,
            "📋 <b>Copy → Send to gemini.google.com:</b>\n\n"
            "<code>Analyze this video: [PASTE LINK]\n\n"
            "Find viral moments. For EACH give:\n"
            "URL: [link]\nSTART: MM:SS\nEND: MM:SS\n"
            "EMOTION: hype/funny/angry/emotional/shocked/happy\n"
            "HOOK: ALL CAPS MAX 6 WORDS\n"
            "LINE1: WHITE TEXT MAX 5 WORDS\n"
            "LINE2: COLORED TEXT MAX 5 WORDS\n"
            "ACTION: *ACTION TEXT*\n"
            "CAPTION: caption with hashtags\n"
            "NUM: 1</code>\n\n"
            "Then paste Gemini response here!")
        return

    if text.startswith("/dl1440 "):
        url = text.replace("/dl1440 ","").strip()
        if not validate_url(url):
            send(chat_id, "❌ Unsupported URL! Use YouTube, Twitch, Instagram, TikTok, etc.")
            return
        thread_pool.submit(download_full, chat_id, url, "1440")
        return

    if text.startswith("/dl720 "):
        url = text.replace("/dl720 ","").strip()
        if not validate_url(url):
            send(chat_id, "❌ Unsupported URL! Use YouTube, Twitch, Instagram, TikTok, etc.")
            return
        thread_pool.submit(download_full, chat_id, url, "720")
        return

    if text.startswith("/dl "):
        url = text.replace("/dl ","").strip()
        if not validate_url(url):
            send(chat_id, "❌ Unsupported URL! Use YouTube, Twitch, Instagram, TikTok, etc.")
            return
        thread_pool.submit(download_full, chat_id, url, "1080")
        return

    if text.startswith("/clip "):
        parts = text.split()
        if len(parts) >= 4:
            url = parts[1]
            if not validate_url(url):
                send(chat_id, "❌ Unsupported URL! Use YouTube, Twitch, Instagram, TikTok, etc.")
                return
            thread_pool.submit(download_only, chat_id, url, parts[2], parts[3], "1080")
        else:
            send(chat_id, "Usage: /clip [url] [start] [end]\nExample: /clip https://youtu.be/xxx 5:00 5:50")
        return

    # Check for URL in message
    for site in SUPPORTED:
        if site in text:
            url = text.split()[0]
            thread_pool.submit(analyze_video, chat_id, url)
            return

    # Check for manual clip data from Gemini
    if "URL:" in text and "START:" in text and "END:" in text:
        # Use compiled regex pattern
        clips_text = CLIP_SPLIT_PATTERN.split(text)
        clips_text = [c for c in clips_text if "URL:" in c and "START:" in c]
        send(chat_id, "✅ Found <b>"+str(len(clips_text))+" clips</b>!")
        for i,ct in enumerate(clips_text):
            d = parse_command(ct)
            if d.get("url") and d.get("start") and d.get("end"):
                # Validate URL
                if not validate_url(d["url"]):
                    send(chat_id, f"❌ Clip {i+1}: Unsupported URL")
                    continue
                # Use thread pool
                thread_pool.submit(
                    edit_clip, chat_id, d["url"], d["start"], d["end"],
                    d.get("emotion","hype"), d.get("hook","WATCH THIS"),
                    d.get("line1","CHECK THIS"), d.get("line2","RIGHT NOW"),
                    d.get("action","*INCREDIBLE*"),
                    d.get("caption","Viral moment! #viral #fyp"),
                    d.get("num",str(i+1))
                )
                time.sleep(2)
        return

    send(chat_id, "Send /start for help! Or paste any YouTube link!")

def get_updates(offset=0):
    url = TG+"/getUpdates?offset="+str(offset)+"&timeout=30"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=35) as r:
            return json.loads(r.read().decode())
    except urllib.error.URLError as e:
        print(f"Network error getting updates: {str(e)[:100]}")
        return {"result":[]}
    except json.JSONDecodeError as e:
        print(f"JSON error getting updates: {str(e)[:100]}")
        return {"result":[]}
    except Exception as e:
        print(f"Unexpected error getting updates: {str(e)[:100]}")
        return {"result":[]}

def main():
    print("ViralCutz Bot starting...")
    print(f"Thread pool configured with max_workers={MAX_WORKERS}")
    tg("sendMessage",{"chat_id":CHAT_ID,"text":"🚀 <b>ViralCutz AI Bot is online!</b>\nSend /start to begin!","parse_mode":"HTML"})
    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            for u in updates.get("result",[]):
                offset = u["update_id"]+1
                msg = u.get("message",{})
                if msg:
                    # Use thread pool instead of creating unbounded threads
                    thread_pool.submit(handle, msg)
        except KeyboardInterrupt:
            print("\nShutting down gracefully...")
            thread_pool.shutdown(wait=True)
            break
        except Exception as e:
            print("Loop error:",str(e)[:100])
            time.sleep(5)

if __name__ == "__main__":
    main()
