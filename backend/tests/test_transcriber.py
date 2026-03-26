import pytest
from unittest.mock import patch, MagicMock
from app.services.transcriber import get_transcript, TranscriptUnavailableError


SAMPLE_SEGMENTS = [
    {"text": "Hello everyone", "start": 0.0, "duration": 3.0},
    {"text": "Today we will talk about Python", "start": 3.0, "duration": 4.0},
    {"text": "Let's get started", "start": 65.0, "duration": 2.5},
]


@patch("app.services.transcriber.YouTubeTranscriptApi.get_transcript")
def test_get_transcript_formats_timestamps(mock_api):
    mock_api.return_value = SAMPLE_SEGMENTS
    result = get_transcript("vid001")
    assert "[0:00]" in result
    assert "[0:03]" in result
    assert "[1:05]" in result
    assert "Hello everyone" in result


@patch("app.services.transcriber.YouTubeTranscriptApi.get_transcript")
def test_transcript_unavailable(mock_api):
    from youtube_transcript_api._errors import TranscriptsDisabled
    mock_api.side_effect = TranscriptsDisabled("vid001")
    with pytest.raises(TranscriptUnavailableError):
        get_transcript("vid001")
