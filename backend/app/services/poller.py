from datetime import datetime
import feedparser

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def poll_channel(channel_id: str, known_video_ids: set[str]) -> list[dict]:
    url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
    feed = feedparser.parse(url)
    new_videos = []
    for entry in feed.entries:
        video_id = entry.get("yt_videoid", "")
        if video_id and video_id not in known_video_ids:
            published = entry.get("published", "")
            try:
                pub_dt = datetime.fromisoformat(published)
            except (ValueError, AttributeError):
                pub_dt = None
            new_videos.append({
                "video_id": video_id,
                "title": entry.get("title", "Untitled"),
                "published_at": pub_dt,
            })
    return new_videos
