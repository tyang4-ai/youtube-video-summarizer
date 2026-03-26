from unittest.mock import MagicMock
from app.services.summarizer import summarize_transcript


def test_short_transcript_single_pass():
    provider = MagicMock()
    provider.summarize.return_value = {
        "summary": "Short overview",
        "sections": [{"timestamp": "0:00", "title": "All", "description": "Everything"}]
    }
    result = summarize_transcript("short transcript", "Title", provider)
    assert result["summary"] == "Short overview"
    provider.summarize.assert_called_once()


def test_long_transcript_triggers_chunking():
    provider = MagicMock()
    provider.summarize.return_value = {
        "summary": "Chunk summary",
        "sections": [{"timestamp": "0:00", "title": "Part", "description": "Desc"}]
    }
    # Create a transcript longer than the token limit
    long_transcript = "\n".join([f"[{i}:00] word " * 100 for i in range(200)])
    result = summarize_transcript(long_transcript, "Title", provider, max_tokens=1000)
    assert provider.summarize.call_count > 1
    assert "summary" in result
