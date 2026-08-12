from pathlib import Path
import re
import uuid
import shutil
import subprocess
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
DOWNLOADS = BASE / "downloads"
DOWNLOADS.mkdir(exist_ok=True)

app = FastAPI(title="One-Click Video Downloader")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


class InfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str


def valid_url(url: str) -> bool:
    return bool(re.match(r"^https?://", url.strip(), re.I))


def run_cmd(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


@app.get("/")
def home():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/api/info")
def info(req: InfoRequest):
    url = req.url.strip()
    if not valid_url(url):
        raise HTTPException(400, "Please enter a valid http/https URL.")

    # This endpoint uses yt-dlp only for URLs/content you are permitted to download.
    result = run_cmd(["yt-dlp", "--extractor-args", "youtube:player_client=android,web", "--no-playlist", "--dump-single-json", "--skip-download", url])
    if result.returncode != 0:
        raise HTTPException(400, "Could not read this URL. It may be unsupported or unavailable.")

    import json
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise HTTPException(500, "The downloader returned invalid metadata.")

    formats = []
    seen = set()

    for f in data.get("formats", []):
        fid = f.get("format_id")
        height = f.get("height")
        ext = f.get("ext")
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        if not fid or not height or vcodec == "none":
            continue

        # Prefer formats that already contain audio, but also allow video-only
        # formats because yt-dlp can merge them with the best available audio.
        label = f"{height}p"
        if acodec != "none":
            label += " • video + audio"

        key = (height, label)
        if key in seen:
            continue
        seen.add(key)

        formats.append({
            "format_id": fid,
            "height": height,
            "label": label,
            "ext": ext or "mp4",
            "has_audio": acodec != "none"
        })

    formats.sort(key=lambda x: x["height"], reverse=True)

    if not formats:
        raise HTTPException(400, "No downloadable video formats were found.")

    return {
        "title": data.get("title") or "video",
        "duration": data.get("duration"),
        "thumbnail": data.get("thumbnail"),
        "formats": formats[:30],
    }


def cleanup(path: Path):
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


@app.post("/api/download")
def download(req: DownloadRequest, background_tasks: BackgroundTasks):
    url = req.url.strip()
    if not valid_url(url):
        raise HTTPException(400, "Invalid URL.")

    job = uuid.uuid4().hex
    output = DOWNLOADS / f"{job}.mp4"

    # Merge selected video with the best available audio and output one MP4.
    # This does not bypass DRM or access controls.
    fmt = req.format_id
    args = [
        "yt-dlp",
        "--no-playlist",
        "--format", f"{fmt}+bestaudio/{fmt}",
        "--merge-output-format", "mp4",
        "--output", str(output),
        url,
    ]

    result = run_cmd(args)
    if result.returncode != 0 or not output.exists():
        cleanup(output)
        raise HTTPException(
            400,
            "Download failed. Check that the URL/content is available and permitted for download."
        )

    background_tasks.add_task(cleanup, output)
    return FileResponse(
        output,
        media_type="video/mp4",
        filename="video.mp4",
        background=background_tasks,
    )
