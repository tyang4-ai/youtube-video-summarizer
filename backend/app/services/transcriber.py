import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

logger = logging.getLogger(__name__)


class TranscriptUnavailableError(Exception):
    pass


def get_transcript(video_id: str) -> str:
    """Fetch transcript using youtube-transcript-api with multiple fallback methods."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=["en"])
    except Exception as e:
        raise TranscriptUnavailableError(f"No transcript for {video_id}: {e}")

    lines = []
    for snippet in transcript:
        ts = _format_timestamp(snippet.start)
        text = snippet.text.strip()
        if text:
            lines.append(f"[{ts}] {text}")

    if not lines:
        raise TranscriptUnavailableError(f"Empty transcript for {video_id}")

    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
