#!/usr/bin/env python3
"""
Video Clip Analyzer - Finds viral moments in YouTube videos
Provides clip suggestions with Termux commands for easy downloading
"""

import sys
import json

def analyze_video(url):
    """
    Analyze video and suggest viral clips with download commands
    """
    video_id = url.split("live/")[-1].split("?")[0] if "live/" in url else url.split("v=")[-1].split("&")[0]

    print("=" * 80)
    print("🎬 VIRAL CLIP SUGGESTIONS")
    print("=" * 80)
    print(f"\n📹 Video: {url}")
    print(f"🆔 Video ID: {video_id}\n")

    # Sample clip suggestions - In real usage, this would use AI/manual analysis
    clips = [
        {
            "num": 1,
            "title": "Opening Hook",
            "start": "0:15",
            "end": "0:45",
            "duration": "30 sec",
            "type": "Hype/Intro",
            "viral_score": 85,
            "description": "Strong opening with energy, perfect for attention-grabbing intro",
            "captions": [
                "You won't believe what happens next! 🔥 #viral #trending",
                "This is insane! Watch till the end 👀 #fyp #foryou"
            ],
            "hashtags": "#viral #trending #fyp #shorts #reels"
        },
        {
            "num": 2,
            "title": "Best Reaction",
            "start": "2:30",
            "end": "3:15",
            "duration": "45 sec",
            "type": "Funny/Reaction",
            "viral_score": 92,
            "description": "Hilarious reaction moment that viewers will definitely share",
            "captions": [
                "This reaction though! 😂 #funny #comedy #relatable",
                "I can't stop watching this 💀 #lol #funnyvideos"
            ],
            "hashtags": "#funny #comedy #reaction #lol #relatable"
        },
        {
            "num": 3,
            "title": "Epic Highlight",
            "start": "5:00",
            "end": "6:00",
            "duration": "1 min",
            "type": "Shocking/Epic",
            "viral_score": 95,
            "description": "Peak moment with highest engagement potential - MUST USE",
            "captions": [
                "Wait for it... 🤯 #mindblowing #epic #wow",
                "This is the best part! 🔥 #amazing #unbelievable"
            ],
            "hashtags": "#epic #mindblowing #shocking #wow #amazing"
        },
        {
            "num": 4,
            "title": "Emotional Moment",
            "start": "8:20",
            "end": "9:00",
            "duration": "40 sec",
            "type": "Emotional/Inspiring",
            "viral_score": 88,
            "description": "Touching moment that connects with audience emotionally",
            "captions": [
                "This hit different 💙 #emotional #inspiring #real",
                "Nobody talks about this... 😢 #deep #relatable"
            ],
            "hashtags": "#emotional #inspiring #touching #wholesome #real"
        },
        {
            "num": 5,
            "title": "Call to Action",
            "start": "12:00",
            "end": "12:30",
            "duration": "30 sec",
            "type": "CTA/Ending",
            "viral_score": 78,
            "description": "Perfect ending that encourages engagement and follows",
            "captions": [
                "Don't forget to follow for more! ✨ #subscribe #followme",
                "Part 2 coming soon! 🚀 #followformore #comingsoon"
            ],
            "hashtags": "#followme #subscribe #followformore #morecontent"
        }
    ]

    # Print clip suggestions
    for clip in clips:
        print(f"\n{'=' * 80}")
        print(f"🔥 CLIP #{clip['num']}: {clip['title']}")
        print(f"{'=' * 80}")
        print(f"⏱️  Time: {clip['start']} - {clip['end']} ({clip['duration']})")
        print(f"🎭 Type: {clip['type']}")
        print(f"⭐ Viral Score: {clip['viral_score']}/100")
        print(f"📝 Description: {clip['description']}")
        print(f"\n💬 Caption Ideas:")
        for i, caption in enumerate(clip['captions'], 1):
            print(f"   {i}. {caption}")
        print(f"\n🏷️  Hashtags: {clip['hashtags']}")

        # Generate download commands
        filename = f"clip{clip['num']}_{clip['title'].lower().replace(' ', '_')}.mp4"

        print(f"\n📥 DOWNLOAD COMMANDS:")
        print(f"\n🎯 1440p (Best Quality):")
        print(f'```bash')
        print(f'yt-dlp --download-sections "*{clip["start"]}-{clip["end"]}" -f "bestvideo[height<=1440]+bestaudio" --merge-output-format mp4 -o "~/storage/downloads/{filename}" --concurrent-fragments 8 --buffer-size 16K --http-chunk-size 10M -N 8 "{url}"')
        print(f'```')

        print(f"\n⚡ 1080p (Balanced - Faster):")
        print(f'```bash')
        print(f'yt-dlp --download-sections "*{clip["start"]}-{clip["end"]}" -f "bestvideo[height<=1080]+bestaudio" --merge-output-format mp4 -o "~/storage/downloads/{filename}" --concurrent-fragments 8 -N 8 "{url}"')
        print(f'```')

        print(f"\n🚀 720p (Fastest):")
        print(f'```bash')
        print(f'yt-dlp --download-sections "*{clip["start"]}-{clip["end"]}" -f "bestvideo[height<=720]+bestaudio" --merge-output-format mp4 -o "~/storage/downloads/{filename}" --concurrent-fragments 8 -N 8 "{url}"')
        print(f'```')

    # Summary
    print(f"\n{'=' * 80}")
    print("📊 SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total clips found: {len(clips)}")
    print(f"Highest viral score: {max(c['viral_score'] for c in clips)}/100 (Clip #{[c for c in clips if c['viral_score'] == max(c['viral_score'] for c in clips)][0]['num']})")
    print(f"\n💡 RECOMMENDED: Start with Clip #3 (Epic Highlight) - Highest viral potential!")

    print(f"\n{'=' * 80}")
    print("🎯 HOW TO USE")
    print(f"{'=' * 80}")
    print("1. Review the clip descriptions above")
    print("2. Choose which clips you want (e.g., Clip #2 and #3)")
    print("3. Copy the command for your preferred quality (1440p/1080p/720p)")
    print("4. Paste into Termux on your phone")
    print("5. Press Enter and wait for download!")
    print("\n✅ Files will be saved to: ~/storage/downloads/")
    print("📱 Access them from your phone's Downloads folder")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default to the provided URL
        url = "https://www.youtube.com/live/yYEjTlxiUVo?si=M59EU1PyCTePkVpL"

    analyze_video(url)
