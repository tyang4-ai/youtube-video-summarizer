import json
import logging
import yt_dlp

logger = logging.getLogger(__name__)


class TranscriptUnavailableError(Exception):
    pass


def get_transcript(video_id: str) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "json3",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise TranscriptUnavailableError(f"Failed to fetch video info for {video_id}: {e}")

    # Try manual subtitles first, then auto-generated
    subtitles = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})

    sub_data = None
    for subs in [subtitles, auto_subs]:
        if "en" in subs:
            for fmt in subs["en"]:
                if fmt.get("ext") == "json3":
                    sub_data = fmt
                    break
            if sub_data:
                break

    if not sub_data or "url" not in sub_data:
        raise TranscriptUnavailableError(f"No English subtitles for {video_id}")

    # Fetch the subtitle data
    import httpx
    try:
        resp = httpx.get(sub_data["url"], timeout=30)
        resp.raise_for_status()
        caption_data = resp.json()
    except Exception as e:
        raise TranscriptUnavailableError(f"Failed to download subtitles for {video_id}: {e}")

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
