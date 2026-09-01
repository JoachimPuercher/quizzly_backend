import json
import yt_dlp


def fetch_youtube(url:str):

# ℹ️ See help(yt_dlp.YoutubeDL) for a list of available options and public functions
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "tmp_filename",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # ℹ️ ydl.sanitize_info makes the info json-serializable
        return(json.dumps(ydl.sanitize_info(info)))