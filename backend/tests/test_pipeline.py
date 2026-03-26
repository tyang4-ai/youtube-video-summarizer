import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Channel, Video
from app.services.pipeline import process_channel


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_happy_path(db):
    ch = Channel(youtube_channel_id="UC1", name="Ch", url="u", poll_interval_minutes=60)
    db.add(ch)
    db.commit()

    settings = MagicMock(PDF_DIR="/tmp/pdfs", ENCRYPTION_KEY="testkey")
    provider = MagicMock()
    provider.summarize.return_value = {
        "summary": "Overview",
        "sections": [{"timestamp": "0:00", "title": "Intro", "description": "Desc"}]
    }

    with patch("app.services.pipeline.poll_channel") as mock_poll, \
         patch("app.services.pipeline.get_transcript") as mock_transcript, \
         patch("app.services.pipeline.generate_pdf") as mock_pdf, \
         patch("app.services.pipeline.send_email_for_video") as mock_email:

        mock_poll.return_value = [{"video_id": "v1", "title": "Vid", "published_at": datetime.utcnow()}]
        mock_transcript.return_value = "[0:00] Hello"
        mock_pdf.return_value = "/tmp/test.pdf"

        process_channel(ch.id, db, settings, provider)

    vid = db.query(Video).filter_by(youtube_video_id="v1").first()
    assert vid is not None
    assert vid.status == "summarized"


def test_transcript_failure_marks_failed(db):
    ch = Channel(youtube_channel_id="UC2", name="Ch2", url="u2")
    db.add(ch)
    db.commit()

    settings = MagicMock(PDF_DIR="/tmp/pdfs", ENCRYPTION_KEY="k")
    provider = MagicMock()

    with patch("app.services.pipeline.poll_channel") as mock_poll, \
         patch("app.services.pipeline.get_transcript") as mock_transcript:

        mock_poll.return_value = [{"video_id": "v2", "title": "V2", "published_at": None}]
        from app.services.transcriber import TranscriptUnavailableError
        mock_transcript.side_effect = TranscriptUnavailableError("no captions")

        process_channel(ch.id, db, settings, provider)

    vid = db.query(Video).filter_by(youtube_video_id="v2").first()
    assert vid.status == "failed"
