import yt_dlp


def fetch_youtube(url: str):
    """Download the audio track of a video and return its local file path."""
    # See help(yt_dlp.YoutubeDL) for all available options.
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "transcribed_data/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)
