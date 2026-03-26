from datetime import datetime
import logging
import os
import yt_dlp

logger = logging.getLogger(__name__)

CHANNEL_URL = "https://www.youtube.com/channel/{channel_id}/videos"
COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cookies.txt")


def poll_channel(channel_id: str, known_video_ids: set[str]) -> list[dict]:
    url = CHANNEL_URL.format(channel_id=channel_id)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": 5,  # Only check last 5 videos
    }
    if os.path.isfile(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.error(f"Failed to fetch channel {channel_id}: {e}")
        return []

    if not info or "entries" not in info:
        return []

    new_videos = []
    for entry in info["entries"]:
        if entry is None:
            continue
        video_id = entry.get("id", "")
        if video_id and video_id not in known_video_ids:
            # Try to parse upload date
            upload_date = entry.get("upload_date", "")
            pub_dt = None
            if upload_date:
                try:
                    pub_dt = datetime.strptime(upload_date, "%Y%m%d")
                except ValueError:
                    pass
            new_videos.append({
                "video_id": video_id,
                "title": entry.get("title", "Untitled"),
                "published_at": pub_dt,
            })
    return new_videos
