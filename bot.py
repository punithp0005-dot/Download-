import os, json, subprocess, urllib.request, re, time, threading

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8616029065:AAGFEklmW_3ZSLmVGEDOr0JwnunkScRRsxc")
CHAT_ID = os.environ.get("CHAT_ID", "8095220898")
NVIDIA_KEY = os.environ.get("NVIDIA_KEY", "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")
WATERMARK = "@_ViralCutz"
OUT = "/tmp/clips"
os.makedirs(OUT, exist_ok=True)
TG = "https://api.telegram.org/bot" + TELEGRAM_TOKEN

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
    except Exception as e:
        print("TG error:", e)
        return {}

def send(chat_id, text):
    tg("sendMessage", {"chat_id":chat_id, "text":text, "parse_mode":"HTML"})

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
        ("Content-Disposition: form-data; name=\"video\"; filename=\"clip.mp4\"\r\n").encode() +
        ("Content-Type: video/mp4\r\n\r\n").encode() +
        vid +
        ("\r\n--"+boundary+"--\r\n").encode()
    )
    req = urllib.request.Request(TG+"/sendVideo", data=body,
          headers={"Content-Type":"multipart/form-data; boundary="+boundary})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print("Video error:", e)

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
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
            return res["choices"][0]["message"]["content"]
    except Exception as e:
        print("Nvidia error:", str(e)[:200])
        return None

def fix_ts(ts):
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        if int(h) == 0:
            return str(int(m))+":"+s
    return ts

def e(t):
    t = str(t)
    t = t.replace("\\", "\\\\")
    t = t.replace("'", "\\'")
    t = t.replace(":", "\\:")
    t = t.replace(",", "\\,")
    t = t.replace("[", "\\[")
    t = t.replace("]", "\\]")
    return t

def download_only(chat_id, url, start, end, quality="1080"):
    ts = str(int(time.time()))
    out = os.path.join(OUT, "clip_"+ts+".mp4")
    start = fix_ts(start)
    end = fix_ts(end)
    send(chat_id, "📥 Downloading "+start+" → "+end+" in "+quality+"p...")
    fmt = "bestvideo[height<="+quality+"]+bestaudio/best[height<="+quality+"]/best"

    # Speed optimizations: concurrent downloads, buffer size, and connection settings
    cmd = ["yt-dlp","--download-sections","*"+start+"-"+end,
           "-f",fmt,"--merge-output-format","mp4",
           "-o",out,"--no-playlist","--retries","5",
           "--concurrent-fragments","8",
           "--buffer-size","16K",
           "--http-chunk-size","10M",
           "--throttled-rate","100K",
           "-N","8",url]
    subprocess.run(cmd, capture_output=True, timeout=600)

    if not os.path.exists(out) or os.path.getsize(out) < 10000:
        cmd2 = ["yt-dlp","--download-sections","*"+start+"-"+end,
                "-f","best","--merge-output-format","mp4",
                "-o",out,"--no-playlist",
                "--concurrent-fragments","8",
                "--buffer-size","16K",
                "-N","8",url]
        subprocess.run(cmd2, capture_output=True, timeout=600)

    if os.path.exists(out) and os.path.getsize(out) > 10000:
        size = round(os.path.getsize(out)/(1024*1024), 1)
        send_video(chat_id, out, "✅ "+quality+"p | "+str(size)+"MB | "+WATERMARK)
        os.remove(out)
        send(chat_id, "✅ Clip sent! Ready to edit in IG Edits! 🎬")
    else:
        send(chat_id, "❌ Download failed! Check URL and timestamps.")

def download_full(chat_id, url, quality="1080"):
    ts = str(int(time.time()))
    out = os.path.join(OUT, "full_"+ts+".mp4")
    send(chat_id, "📥 Downloading full video in "+quality+"p...")
    fmt = "bestvideo[height<="+quality+"]+bestaudio/best[height<="+quality+"]/best"

    # Speed optimizations for full video downloads
    cmd = ["yt-dlp","-f",fmt,"--merge-output-format","mp4",
           "-o",out,"--no-playlist","--retries","5",
           "--concurrent-fragments","8",
           "--buffer-size","16K",
           "--http-chunk-size","10M",
           "--throttled-rate","100K",
           "-N","8",url]
    subprocess.run(cmd, capture_output=True, timeout=600)

    if not os.path.exists(out) or os.path.getsize(out) < 10000:
        cmd2 = ["yt-dlp","-f","best","--merge-output-format","mp4",
                "-o",out,"--no-playlist",
                "--concurrent-fragments","8",
                "--buffer-size","16K",
                "-N","8",url]
        subprocess.run(cmd2, capture_output=True, timeout=600)

    if os.path.exists(out) and os.path.getsize(out) > 10000:
        size = round(os.path.getsize(out)/(1024*1024), 1)
        send_video(chat_id, out, "✅ "+quality+"p | "+str(size)+"MB | "+WATERMARK)
        os.remove(out)
        send(chat_id, "✅ Video sent! 🎬")
    else:
        send(chat_id, "❌ Download failed!")

def edit_clip(chat_id, url, start, end, emotion, hook, line1, line2, action, caption, num):
    ts = str(int(time.time()))
    raw   = os.path.join(OUT, "raw_"+ts+".mp4")
    sq    = os.path.join(OUT, "sq_"+ts+".mp4")
    voice = os.path.join(OUT, "voice_"+ts+".mp3")
    final = os.path.join(OUT, "final_"+ts+".mp4")

    start = fix_ts(start)
    end   = fix_ts(end)

    send(chat_id, "📥 Downloading clip "+str(num)+"... "+start+" → "+end)

    # Speed optimizations: concurrent fragments, buffering, and multiple connections
    cmd = ["yt-dlp","--download-sections","*"+start+"-"+end,
           "-f","bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
           "--merge-output-format","mp4","-o",raw,"--no-playlist","--retries","5",
           "--concurrent-fragments","8",
           "--buffer-size","16K",
           "--http-chunk-size","10M",
           "-N","8",url]
    subprocess.run(cmd, capture_output=True, timeout=600)

    if not os.path.exists(raw) or os.path.getsize(raw) < 10000:
        cmd2 = ["yt-dlp","--download-sections","*"+start+"-"+end,
                "-f","best","--merge-output-format","mp4","-o",raw,"--no-playlist",
                "--concurrent-fragments","8",
                "--buffer-size","16K",
                "-N","8",url]
        subprocess.run(cmd2, capture_output=True, timeout=600)

    if not os.path.exists(raw) or os.path.getsize(raw) < 10000:
        send(chat_id, "❌ Download failed clip "+str(num))
        return

    send(chat_id, "🎤 Adding voice intro...")
    voice_text = hook+". "+line1+" "+line2+". Watch what happens!"
    has_voice = make_voice(voice_text, voice)

    send(chat_id, "🎨 Editing in "+emotion.upper()+" style...")

    fx = FX.get(emotion, FX["hype"])
    tc = fx["tc"]
    bc = fx["bc"]

    # Step 1: Make 1:1 blur background - faster preset
    r1 = subprocess.run([
        "ffmpeg","-y","-i",raw,
        "-filter_complex",
        "[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,boxblur=20:20[bg];"
        "[0:v]scale=810:810:force_original_aspect_ratio=decrease,pad=810:810:(ow-iw)/2:(oh-ih)/2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]",
        "-map","[v]","-map","0:a",
        "-c:v","libx264","-preset","veryfast","-crf","18",
        "-c:a","aac","-b:a","192k", sq
    ], capture_output=True, timeout=300)

    src = sq if r1.returncode == 0 and os.path.exists(sq) else raw

    # Step 2: Add subtitles using simple drawtext without fontfile
    h_e   = e(hook)
    l1_e  = e(line1)
    l2_e  = e(line2)
    act_e = e(action)
    wm_e  = e(WATERMARK)

    vf = (
        fx["eq"]+","
        "drawtext=text='"+h_e+"':fontcolor=white:fontsize=55:font=Sans:"
        "x=(w-text_w)/2:y=50:shadowcolor=black:shadowx=2:shadowy=2:"
        "box=1:boxcolor=black@0.6:boxborderw=8:enable='between(t,0,3)',"
        "drawtext=text='"+l1_e+"':fontcolor=white:fontsize=58:font=Sans:"
        "x=(w-text_w)/2:y=h-200:shadowcolor=black:shadowx=2:shadowy=2:"
        "enable='between(t,3,15)',"
        "drawtext=text='"+l2_e+"':fontcolor="+tc+":fontsize=62:font=Sans:"
        "x=(w-text_w)/2:y=h-130:shadowcolor=black:shadowx=3:shadowy=3:"
        "box=1:boxcolor="+bc+":boxborderw=10:enable='between(t,15,32)',"
        "drawtext=text='"+act_e+"':fontcolor="+tc+":fontsize=58:font=Sans:"
        "x=(w-text_w)/2:y=h-160:shadowcolor=black:shadowx=3:shadowy=3:"
        "box=1:boxcolor="+bc+":boxborderw=10:enable='between(t,32,55)',"
        "drawtext=text='"+wm_e+"':fontcolor=white@0.15:fontsize=20:font=Sans:"
        "x=(w-text_w)/2:y=h-30"
    )

    if fx["gl"]:
        vf += ",rgbashift=rh=3:rv=0:bh=-3:bv=0:enable='between(t,14.9,15.1)'"
        vf += ",rgbashift=rh=4:rv=1:bh=-4:bv=-1:enable='between(t,31.9,32.1)'"

    if has_voice and os.path.exists(voice):
        r2 = subprocess.run([
            "ffmpeg","-y","-i",src,"-i",voice,
            "-filter_complex",
            "[0:v]"+vf+"[v];"
            "[1:a]volume=2.0[va];"
            "[0:a]"+fx["af"]+"[oa];"
            "[va][oa]amix=inputs=2:duration=shortest:weights=3 1[a]",
            "-map","[v]","-map","[a]",
            "-c:v","libx264","-preset","veryfast","-crf","18",
            "-b:v","4000k","-c:a","aac","-b:a","192k",final
        ], capture_output=True, text=True, timeout=300)
    else:
        r2 = subprocess.run([
            "ffmpeg","-y","-i",src,
            "-vf",vf,"-af",fx["af"],
            "-c:v","libx264","-preset","veryfast","-crf","18",
            "-b:v","4000k","-c:a","aac","-b:a","192k",final
        ], capture_output=True, text=True, timeout=300)

    print("Edit rc:", r2.returncode)
    if r2.returncode != 0:
        print("Edit err:", r2.stderr[-300:])
        # Fallback - just color grade with faster preset
        subprocess.run([
            "ffmpeg","-y","-i",src,
            "-vf",fx["eq"],"-af",fx["af"],
            "-c:v","libx264","-preset","veryfast","-crf","18",
            "-c:a","aac",final
        ], capture_output=True, timeout=300)

    for f in [raw,sq,voice]:
        if os.path.exists(f): os.remove(f)

    if os.path.exists(final) and os.path.getsize(final) > 10000:
        send_video(chat_id, final, caption)
        os.remove(final)
        send(chat_id, "✅ <b>Clip "+str(num)+" done!</b>\n\n📝 Caption:\n"+caption)
    else:
        send(chat_id, "❌ Edit failed clip "+str(num))

def parse_command(text):
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

def analyze_video(chat_id, url):
    send(chat_id, "📡 Getting video info...")
    cmd = ["yt-dlp","--dump-json","--no-playlist",url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    title = "Unknown"; channel = "Unknown"; duration = 0
    try:
        info = json.loads(r.stdout)
        title = info.get("title","Unknown")
        channel = info.get("uploader","Unknown")
        duration = info.get("duration",0)
        send(chat_id, "✅ <b>"+title+"</b>\nChannel: "+channel)
    except: pass

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

    clips_text = re.split(r"(?=URL:)", response)
    clips_text = [c for c in clips_text if "URL:" in c and "START:" in c]
    if not clips_text:
        send(chat_id, "❌ No clips found. Try /prompt!"); return

    send(chat_id, "🎬 Found <b>"+str(len(clips_text))+" viral moments!</b>\nProcessing...")
    for i, ct in enumerate(clips_text):
        d = parse_command(ct)
        if d.get("url") and d.get("start") and d.get("end"):
            threading.Thread(target=edit_clip, args=(
                chat_id, d["url"], d["start"], d["end"],
                d.get("emotion","hype"), d.get("hook","WATCH THIS"),
                d.get("line1","CHECK THIS"), d.get("line2","RIGHT NOW"),
                d.get("action","*INCREDIBLE*"),
                d.get("caption","Viral moment! #viral #fyp"),
                d.get("num",str(i+1))
            ), daemon=True).start()
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
            "/clip [url] [start] [end] → Download clip only (1080p)\n"
            "/clip1440 [url] [start] [end] → Download clip in 1440p\n"
            "/dl [url] → Download full video 1080p\n"
            "/dl1440 [url] → Download 1440p\n"
            "/dl720 [url] → Download 720p\n"
            "/prompt → Get Gemini prompt for manual use\n\n"
            "<b>Example:</b>\n"
            "<code>/clip https://youtu.be/xxx 5:00 5:50</code>\n"
            "<code>/clip1440 https://youtu.be/xxx 5:00 5:50</code>\n\n"
            "⚡ <b>Now with FASTER downloads!</b> Using:\n"
            "• 8 concurrent fragment downloads\n"
            "• Optimized buffering (16K buffer + 10M chunks)\n"
            "• 8 parallel connections\n"
            "• Faster ffmpeg encoding (veryfast preset)")
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
        threading.Thread(target=download_full, args=(chat_id,url,"1440"), daemon=True).start()
        return

    if text.startswith("/dl720 "):
        url = text.replace("/dl720 ","").strip()
        threading.Thread(target=download_full, args=(chat_id,url,"720"), daemon=True).start()
        return

    if text.startswith("/dl "):
        url = text.replace("/dl ","").strip()
        threading.Thread(target=download_full, args=(chat_id,url,"1080"), daemon=True).start()
        return

    if text.startswith("/clip1440 "):
        parts = text.split()
        if len(parts) >= 4:
            threading.Thread(target=download_only,
                args=(chat_id,parts[1],parts[2],parts[3],"1440"),
                daemon=True).start()
        else:
            send(chat_id, "Usage: /clip1440 [url] [start] [end]\nExample: /clip1440 https://youtu.be/xxx 5:00 5:50")
        return

    if text.startswith("/clip "):
        parts = text.split()
        if len(parts) >= 4:
            threading.Thread(target=download_only,
                args=(chat_id,parts[1],parts[2],parts[3],"1080"),
                daemon=True).start()
        else:
            send(chat_id, "Usage: /clip [url] [start] [end]\nExample: /clip https://youtu.be/xxx 5:00 5:50")
        return

    for site in SUPPORTED:
        if site in text:
            url = text.split()[0]
            threading.Thread(target=analyze_video, args=(chat_id,url), daemon=True).start()
            return

    if "URL:" in text and "START:" in text and "END:" in text:
        clips_text = re.split(r"(?=URL:)", text)
        clips_text = [c for c in clips_text if "URL:" in c and "START:" in c]
        send(chat_id, "✅ Found <b>"+str(len(clips_text))+" clips</b>!")
        for i,ct in enumerate(clips_text):
            d = parse_command(ct)
            if d.get("url") and d.get("start") and d.get("end"):
                threading.Thread(target=edit_clip, args=(
                    chat_id, d["url"], d["start"], d["end"],
                    d.get("emotion","hype"), d.get("hook","WATCH THIS"),
                    d.get("line1","CHECK THIS"), d.get("line2","RIGHT NOW"),
                    d.get("action","*INCREDIBLE*"),
                    d.get("caption","Viral moment! #viral #fyp"),
                    d.get("num",str(i+1))
                ), daemon=True).start()
                time.sleep(2)
        return

    send(chat_id, "Send /start for help! Or paste any YouTube link!")

def get_updates(offset=0):
    url = TG+"/getUpdates?offset="+str(offset)+"&timeout=30"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=35) as r:
            return json.loads(r.read().decode())
    except: return {"result":[]}

def main():
    print("ViralCutz Bot starting...")
    tg("sendMessage",{"chat_id":CHAT_ID,"text":"🚀 <b>ViralCutz AI Bot is online!</b>\nSend /start to begin!","parse_mode":"HTML"})
    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            for u in updates.get("result",[]):
                offset = u["update_id"]+1
                msg = u.get("message",{})
                if msg:
                    threading.Thread(target=handle,args=(msg,),daemon=True).start()
        except Exception as e:
            print("Loop error:",str(e)[:100])
            time.sleep(5)

if __name__ == "__main__":
    main()
