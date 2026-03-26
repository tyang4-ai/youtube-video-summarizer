import pytest
from pydantic import ValidationError
from app.schemas import ChannelCreate, ChannelUpdate, EmailConfigResponse, SummaryResponse


def test_channel_create_valid():
    c = ChannelCreate(url="https://youtube.com/@fireship")
    assert c.poll_interval_minutes == 60


def test_channel_create_missing_url():
    with pytest.raises(ValidationError):
        ChannelCreate()


def test_channel_update_partial():
    u = ChannelUpdate(is_active=False)
    assert u.is_active is False
    assert u.poll_interval_minutes is None


def test_email_config_masks_password():
    r = EmailConfigResponse(
        id=1, smtp_host="smtp.gmail.com", smtp_port=587,
        smtp_user="user", smtp_password="secret123",
        sender_email="a@b.com", recipients=["x@y.com"], is_active=True
    )
    assert r.smtp_password == "******"


def test_summary_response_parses_timestamps():
    s = SummaryResponse(
        id=1, video_id=1, summary_text="overview",
        timestamps=[{"timestamp": "0:00", "title": "Intro", "description": "desc"}],
        pdf_path="/tmp/t.pdf", email_sent=False, created_at="2026-01-01T00:00:00"
    )
    assert len(s.timestamps) == 1
    assert s.timestamps[0]["timestamp"] == "0:00"
