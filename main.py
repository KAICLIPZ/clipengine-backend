import os
import json
import subprocess
import yt_dlp
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from faster_whisper import WhisperModel
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

class ClipRequest(BaseModel):
    youtube_url: str
    admin_password: str

def process_video_pipeline(url: str, request_id: str):
    try:
        output_video = f"video_{request_id}.mp4"
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_video,
            'nocheckcertificate': True,
            'merge_output_format': 'mp4'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        audio_track = f"audio_{request_id}.wav"
        subprocess.run(f'ffmpeg -y -i "{output_video}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio_track}"', shell=True)
        
        segments, info = whisper_model.transcribe(audio_track, beam_size=3, word_timestamps=True)
        print(f"Successfully processed clip batch token: {request_id}")
    except Exception as e:
        print(f"Error handling task sequence: {e}")

@app.post("/api/generate-shorts")
async def generate_shorts(request: ClipRequest, background_tasks: BackgroundTasks):
    SECRET_PASSWORD = os.getenv("ADMIN_PASSWORD", "MasterClipper2026")
    if request.admin_password != SECRET_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized: Incorrect admin credentials.")

    if not request.youtube_url:
        raise HTTPException(status_code=400, detail="Missing URL input parameter string.")
        
    import uuid
    request_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(process_video_pipeline, request.youtube_url, request_id)
    
    return {"status": "processing", "request_id": request_id}
