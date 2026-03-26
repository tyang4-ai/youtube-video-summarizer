from sqlalchemy.orm import Session
from app.models import JobLog


def log_job(db: Session, action: str, status: str,
            channel_id: int = None, video_id: int = None, error: str = None) -> JobLog:
    entry = JobLog(
        channel_fk=channel_id,
        video_fk=video_id,
        action=action,
        status=status,
        error_message=error,
    )
    db.add(entry)
    db.commit()
    return entry
