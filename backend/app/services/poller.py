from datetime import datetime
import logging
import os
import httpx

logger = logging.getLogger(__name__)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


def poll_channel(channel_id: str, known_video_ids: set[str]) -> list[dict]:
    """Fetch latest videos from a YouTube channel using the Data API v3."""
    api_key = YOUTUBE_API_KEY
    if not api_key:
        logger.error("YOUTUBE_API_KEY not set")
        return []

    # Search for recent videos from the channel
    params = {
        "key": api_key,
        "channelId": channel_id,
        "part": "snippet",
        "order": "date",
        "maxResults": 5,
        "type": "video",
    }

    try:
        resp = httpx.get(f"{YOUTUBE_API_URL}/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch channel {channel_id}: {e}")
        return []

    new_videos = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId", "")
        if video_id and video_id not in known_video_ids:
            snippet = item.get("snippet", {})
            pub_dt = None
            published = snippet.get("publishedAt", "")
            if published:
                try:
                    pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except ValueError:
                    pass
            new_videos.append({
                "video_id": video_id,
                "title": snippet.get("title", "Untitled"),
                "published_at": pub_dt,
            })
    return new_videos
