# ClipDrop — One-Click Video Downloader

A local FastAPI web app that analyzes permitted video URLs, lets the user choose an available quality, and returns one MP4 containing video + audio.

## Requirements

- Windows/macOS/Linux
- Python 3.10+
- FFmpeg installed and available in PATH
- yt-dlp installed and available in PATH

## Windows setup

1. Install Python from the official Python website.
2. Install FFmpeg and add its `bin` directory to PATH.
3. Open PowerShell in this project folder.
4. Install Python dependencies:

```powershell
py -m pip install -r requirements.txt
```

5. Install/update yt-dlp:

```powershell
py -m pip install -U yt-dlp
```

If `yt-dlp` is not found as a command, use:

```powershell
py -m yt_dlp --version
```

and change the `yt-dlp` command in `server.py` to `py -m yt_dlp`.

## Run

```powershell
py -m uvicorn server:app --reload
```

Open:

http://127.0.0.1:8000

## Notes

- The app intentionally uses `--no-playlist`.
- It does not bypass DRM, login requirements, paywalls, or access controls.
- Use only URLs/content you are authorized to download and where downloading is permitted.
- For production, add authentication, rate limiting, storage quotas, HTTPS, job queues, and strict resource limits.
