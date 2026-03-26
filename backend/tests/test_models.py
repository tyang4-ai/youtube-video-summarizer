from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import pytest
from app.models import Base, Channel, Video, Summary, EmailConfig, JobLog


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_create_channel(db):
    ch = Channel(youtube_channel_id="UC123", name="Test", url="https://youtube.com/@test", poll_interval_minutes=60)
    db.add(ch)
    db.commit()
    assert ch.id is not None
    assert ch.is_active is True
    assert ch.created_at is not None


def test_channel_unique_constraint(db):
    ch1 = Channel(youtube_channel_id="UC123", name="A", url="url1")
    ch2 = Channel(youtube_channel_id="UC123", name="B", url="url2")
    db.add(ch1)
    db.commit()
    db.add(ch2)
    with pytest.raises(IntegrityError):
        db.commit()


def test_create_video_with_channel(db):
    ch = Channel(youtube_channel_id="UC123", name="Test", url="url")
    db.add(ch)
    db.commit()
    vid = Video(channel_fk=ch.id, youtube_video_id="vid1", title="Video 1", status="pending")
    db.add(vid)
    db.commit()
    assert vid.id is not None
    assert vid.status == "pending"


def test_create_summary(db):
    ch = Channel(youtube_channel_id="UC1", name="C", url="u")
    db.add(ch)
    db.commit()
    vid = Video(channel_fk=ch.id, youtube_video_id="v1", title="T", status="summarized")
    db.add(vid)
    db.commit()
    s = Summary(video_id=vid.id, summary_text="overview", timestamps_json="[]", pdf_path="/tmp/t.pdf")
    db.add(s)
    db.commit()
    assert s.email_sent is False


def test_create_email_config(db):
    ec = EmailConfig(smtp_host="smtp.gmail.com", smtp_port=587, smtp_user="u", smtp_password="p", sender_email="a@b.com", recipients_json='["x@y.com"]')
    db.add(ec)
    db.commit()
    assert ec.is_active is True


def test_create_job_log(db):
    jl = JobLog(action="poll", status="success")
    db.add(jl)
    db.commit()
    assert jl.created_at is not None
