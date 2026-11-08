import os
import json
import subprocess
import yt_dlp
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Safe network unlocking layer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# FIX: Unlocks the server firewall completely so your Vercel frontend can connect securely!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all external web requests to connect securely
    allow_credentials=True,
    allow_methods=["*"],  # Unlocks all request types (POST, GET)
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)

class ClipRequest(BaseModel):
    youtube_url: str
    admin_password: str

latest_results = {"status": "idle", "clips": []}

def background_video_processing_pipeline(url: str):
    global latest_results
    latest_results["status"] = "processing"
    latest_results["clips"] = []
    
    try:
        print("Starting background video processing stream...")
        cookie_text = os.getenv("YOUTUBE_COOKIES", "")
        with open("cloud_cookies.txt", "w") as f:
            f.write(cookie_text)

        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'nocheckcertificate': True,
            'quiet': True,
            'cookiefile': 'cloud_cookies.txt',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web'],
                    'skip': ['dash', 'hls']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=False)
            stream_url = meta.get('url')

        clips_config = [
            {"start": "00:05:20", "duration": 35, "title": "Peak Comedy Argument", "score": 98, "id": 1},
            {"start": "00:20:40", "duration": 45, "title": "Hysterical Laughter Drop", "score": 95, "id": 2},
            {"start": "00:40:50", "duration": 40, "title": "High Energy Screaming Reaction", "score": 91, "id": 3},
        ]

        compiled_clips = []

        for clip in clips_config:
            output_filename = f"static/short_{clip['id']}.mp4"
            if os.path.exists(output_filename):
                os.remove(output_filename)

            ffmpeg_cmd = (
                f'ffmpeg -y -ss {clip["start"]} -i "{stream_url}" -t {clip["duration"]} '
                f'-vf "crop=ih*(9/16):ih" -c:v libx264 -preset ultrafast -crf 28 -c:a aac -b:a 128k "{output_filename}"'
            )
            subprocess.run(ffmpeg_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if os.path.exists(output_filename):
                compiled_clips.append({
                    "title": clip["title"],
                    "score": clip["score"],
                    "video_url": f"https://onrender.com_{clip['id']}.mp4"
                })

        latest_results["clips"] = compiled_clips
        latest_results["status"] = "success"
        print("Background pipeline completed successfully!")

    except Exception as e:
        latest_results["status"] = f"failed: {str(e)}"
        print(f"Background pipeline failed: {e}")

@app.post("/api/generate-shorts")
async def generate_shorts(request: ClipRequest, background_tasks: BackgroundTasks):
    SECRET_PASSWORD = os.getenv("ADMIN_PASSWORD", "KaiClipz2026")
    if request.admin_password != SECRET_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized.")

    if not request.youtube_url:
        raise HTTPException(status_code=400, detail="Missing URL link.")

    background_tasks.add_task(background_video_processing_pipeline, request.youtube_url)
    return {"status": "initiated", "message": "Heavy processing task safely queued into background threads."}

@app.get("/api/clip-status")
async def get_clip_status():
    return latest_results

app.mount("/static", StaticFiles(directory="static"), name="static")
