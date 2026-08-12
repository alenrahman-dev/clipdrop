from pathlib import Path
import re
import uuid
import subprocess
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE = Path(__file__).resolve().parent
DOWNLOADS = BASE / "downloads"
DOWNLOADS.mkdir(exist_ok=True)


# --------------------------------------------------
# FastAPI
# --------------------------------------------------

app = FastAPI(title="ClipDrop Video Downloader")

app.mount(
    "/static",
    StaticFiles(directory=BASE / "static"),
    name="static"
)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class InfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def valid_url(url: str) -> bool:
    return bool(
        re.match(
            r"^https?://",
            url.strip(),
            re.I
        )
    )


def run_cmd(args):
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )


def cleanup(path: Path):
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


# --------------------------------------------------
# Home page
# --------------------------------------------------

@app.get("/")
def home():
    return FileResponse(
        BASE / "static" / "index.html"
    )


# --------------------------------------------------
# Get video information
# --------------------------------------------------

@app.post("/api/info")
def info(req: InfoRequest):

    url = req.url.strip()

    if not valid_url(url):
        raise HTTPException(
            400,
            "Please enter a valid http/https URL."
        )

    result = run_cmd([
        "yt-dlp",
        "--no-playlist",
        "--dump-single-json",
        "--skip-download",
        url
    ])

    # Print the real yt-dlp error to Render logs
    if result.returncode != 0:

        print("========== YT-DLP ERROR ==========")
        print(result.stderr)
        print("==================================")

        raise HTTPException(
            400,
            "Could not read this URL. It may be unsupported, unavailable, or not permitted for download."
        )

    try:
        data = json.loads(result.stdout)

    except json.JSONDecodeError:

        print("========== INVALID YT-DLP JSON ==========")
        print(result.stdout)
        print("=========================================")

        raise HTTPException(
            500,
            "The downloader returned invalid metadata."
        )

    formats = []
    seen = set()

    for f in data.get("formats", []):

        fid = f.get("format_id")
        height = f.get("height")
        ext = f.get("ext")
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")

        if not fid:
            continue

        if not height:
            continue

        if vcodec == "none":
            continue

        label = f"{height}p"

        if acodec != "none":
            label += " • video + audio"
        else:
            label += " • video"

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

    formats.sort(
        key=lambda x: x["height"],
        reverse=True
    )

    if not formats:

        raise HTTPException(
            400,
            "No downloadable video formats were found."
        )

    return {
        "title": data.get("title") or "video",
        "duration": data.get("duration"),
        "thumbnail": data.get("thumbnail"),
        "formats": formats[:30],
    }


# --------------------------------------------------
# Download video
# --------------------------------------------------

@app.post("/api/download")
def download(
    req: DownloadRequest,
    background_tasks: BackgroundTasks
):

    url = req.url.strip()

    if not valid_url(url):
        raise HTTPException(
            400,
            "Invalid URL."
        )

    job = uuid.uuid4().hex

    output = DOWNLOADS / f"{job}.mp4"

    fmt = req.format_id

    # Selected video + best available audio.
    # If the selected format already contains audio,
    # yt-dlp can use it directly.
    format_selector = f"{fmt}+bestaudio/{fmt}"

    args = [
        "yt-dlp",

        "--no-playlist",

        "--format",
        format_selector,

        "--merge-output-format",
        "mp4",

        "--output",
        str(output),

        url,
    ]

    result = run_cmd(args)

    if result.returncode != 0 or not output.exists():

        print("========== DOWNLOAD ERROR ==========")
        print(result.stderr)
        print("====================================")

        cleanup(output)

        raise HTTPException(
            400,
            "Download failed. Check that the URL/content is available and permitted for download."
        )

    # Delete the temporary file after the response
    background_tasks.add_task(
        cleanup,
        output
    )

    return FileResponse(
        output,
        media_type="video/mp4",
        filename="video.mp4",
        background=background_tasks
    )
