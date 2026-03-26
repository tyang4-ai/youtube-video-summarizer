from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.models import Channel
from app.services.pipeline import process_channel


def create_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler()


def register_channel_job(scheduler, channel, db_factory, settings, provider):
    job_id = f"channel_{channel.id}"
    scheduler.add_job(
        _run_pipeline,
        "interval",
        minutes=channel.poll_interval_minutes,
        id=job_id,
        args=[channel.id, db_factory, settings, provider],
        replace_existing=True,
    )


def remove_channel_job(scheduler, channel_id: int):
    job_id = f"channel_{channel_id}"
    scheduler.remove_job(job_id)


def reschedule_channel_job(scheduler, channel, db_factory, settings, provider):
    try:
        remove_channel_job(scheduler, channel.id)
    except Exception:
        pass
    if channel.is_active:
        register_channel_job(scheduler, channel, db_factory, settings, provider)


def startup_register_all(scheduler, db: Session, db_factory, settings, provider):
    channels = db.query(Channel).filter_by(is_active=True).all()
    for ch in channels:
        register_channel_job(scheduler, ch, db_factory, settings, provider)


def _run_pipeline(channel_id: int, db_factory, settings, provider):
    db = db_factory()
    try:
        process_channel(channel_id, db, settings, provider)
    finally:
        db.close()
