import os

import yt_dlp
from django.conf import settings

# Longer videos take too long to transcribe within a single request.
MAX_VIDEO_DURATION_SECONDS = 20 * 60

DOWNLOAD_DIR = settings.BASE_DIR / "transcribed_data"


class VideoTooLongError(Exception):
    """The video exceeds the duration limit or has no known duration."""


def fetch_youtube(url: str) -> str:
    """Download the audio track of a video and return its local file path."""
    # See help(yt_dlp.YoutubeDL) for all available options.
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if settings.YTDLP_POT_PROVIDER_URL:
        # The bgutil plugin asks this service for the proof-of-origin tokens
        # YouTube demands from datacenter IPs. Values are lists, that is how
        # yt-dlp represents extractor arguments.
        ydl_opts["extractor_args"] = {
            "youtubepot-bgutilhttp": {
                "base_url": [settings.YTDLP_POT_PROVIDER_URL],
            }
        }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Look at the metadata first so nothing is downloaded for a
        # rejected video.
        info = ydl.extract_info(url, download=False)
        duration = info.get("duration")
        if duration is None or duration > MAX_VIDEO_DURATION_SECONDS:
            minutes = MAX_VIDEO_DURATION_SECONDS // 60
            raise VideoTooLongError(
                f"Videos longer than {minutes} minutes are not supported."
            )

        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def remove_download(path: str) -> None:
    """Delete a downloaded file, ignoring one that is already gone."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
