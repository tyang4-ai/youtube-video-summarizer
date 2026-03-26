import logging
import os
import httpx

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


class TranscriptUnavailableError(Exception):
    pass


def get_transcript(video_id: str) -> str:
    """Fetch transcript using YouTube's timedtext API directly."""
    # First, get the video page to find caption tracks
    try:
        resp = httpx.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True,
            timeout=30,
        )
        resp.raise_for_status()
        page = resp.text
    except Exception as e:
        raise TranscriptUnavailableError(f"Failed to fetch video page for {video_id}: {e}")

    # Extract captions URL from the page
    import re
    import json

    # Find the captions data in the page source
    caption_match = re.search(r'"captions":\s*(\{.*?"playerCaptionsTracklistRenderer".*?\})\s*,\s*"videoDetails"', page)
    if not caption_match:
        raise TranscriptUnavailableError(f"No captions found for {video_id}")

    try:
        captions_data = json.loads(caption_match.group(1))
        tracks = captions_data.get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    except (json.JSONDecodeError, KeyError):
        raise TranscriptUnavailableError(f"Failed to parse captions data for {video_id}")

    if not tracks:
        raise TranscriptUnavailableError(f"No caption tracks for {video_id}")

    # Find English track (prefer manual over auto-generated)
    selected_track = None
    for track in tracks:
        lang = track.get("languageCode", "")
        if lang == "en":
            selected_track = track
            if track.get("kind") != "asr":  # Prefer non-ASR (manual) captions
                break

    # Fallback to first available track
    if not selected_track:
        selected_track = tracks[0]

    base_url = selected_track.get("baseUrl", "")
    if not base_url:
        raise TranscriptUnavailableError(f"No caption URL for {video_id}")

    # Fetch captions as JSON
    try:
        caption_url = f"{base_url}&fmt=json3"
        resp = httpx.get(caption_url, timeout=30)
        resp.raise_for_status()
        caption_data = resp.json()
    except Exception as e:
        raise TranscriptUnavailableError(f"Failed to download captions for {video_id}: {e}")

    # Parse json3 format into timestamped text
    events = caption_data.get("events", [])
    lines = []
    for event in events:
        if "segs" not in event:
            continue
        start_ms = event.get("tStartMs", 0)
        text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
        if text and text != "\n":
            ts = _format_timestamp(start_ms / 1000)
            lines.append(f"[{ts}] {text}")

    if not lines:
        raise TranscriptUnavailableError(f"Empty transcript for {video_id}")

    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
