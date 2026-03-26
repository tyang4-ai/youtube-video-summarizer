from pathlib import Path
from unittest.mock import patch, MagicMock
import feedparser
from app.services.poller import poll_channel

FIXTURE = Path(__file__).parent / "fixtures" / "sample_rss.xml"
PARSED_FEED = feedparser.parse(FIXTURE.read_text())


@patch("app.services.poller.feedparser.parse")
def test_poll_returns_new_videos(mock_parse):
    mock_parse.return_value = PARSED_FEED
    results = poll_channel("UC123", known_video_ids=set())
    assert len(results) == 3
    assert results[0]["video_id"] == "vid001"
    assert results[0]["title"] == "First Video"


@patch("app.services.poller.feedparser.parse")
def test_poll_filters_known_videos(mock_parse):
    mock_parse.return_value = PARSED_FEED
    results = poll_channel("UC123", known_video_ids={"vid001", "vid003"})
    assert len(results) == 1
    assert results[0]["video_id"] == "vid002"


@patch("app.services.poller.feedparser.parse")
def test_poll_empty_feed(mock_parse):
    mock_parse.return_value = MagicMock(entries=[])
    results = poll_channel("UC123", known_video_ids=set())
    assert results == []
