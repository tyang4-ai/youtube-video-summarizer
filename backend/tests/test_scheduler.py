from unittest.mock import MagicMock
from app.services.scheduler import register_channel_job, remove_channel_job


def test_register_adds_interval_job():
    sched = MagicMock()
    channel = MagicMock(id=1, poll_interval_minutes=30, youtube_channel_id="UC1")
    register_channel_job(sched, channel, MagicMock(), MagicMock(), MagicMock())
    sched.add_job.assert_called_once()


def test_remove_job():
    sched = MagicMock()
    remove_channel_job(sched, 1)
    sched.remove_job.assert_called_once_with("channel_1")
