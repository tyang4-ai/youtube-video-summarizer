from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Channel, Video, Summary, JobLog
from app.schemas import DashboardResponse, ActivityItem

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    channel_count = db.query(func.count(Channel.id)).scalar() or 0
    videos_processed = (
        db.query(func.count(Video.id))
        .filter(Video.status == "summarized")
        .scalar()
        or 0
    )
    emails_sent = (
        db.query(func.count(Summary.id))
        .filter(Summary.email_sent == True)  # noqa: E712
        .scalar()
        or 0
    )

    channels = db.query(Channel).all()
    channel_data = []
    for ch in channels:
        videos = db.query(Video).filter_by(channel_fk=ch.id).order_by(Video.created_at.desc()).limit(5).all()
        channel_data.append({
            "id": ch.id,
            "name": ch.name,
            "is_active": ch.is_active,
            "last_polled_at": ch.last_polled_at.isoformat() if ch.last_polled_at else None,
            "videos": [
                {
                    "id": v.id,
                    "title": v.title,
                    "status": v.status,
                    "published_at": v.published_at.isoformat() if v.published_at else None,
                }
                for v in videos
            ],
        })

    return {
        "channel_count": channel_count,
        "videos_processed": videos_processed,
        "emails_sent": emails_sent,
        "channels": channel_data,
    }


@router.get("/activity", response_model=list[ActivityItem])
def get_activity(limit: int = 50, db: Session = Depends(get_db)):
    logs = (
        db.query(JobLog)
        .order_by(JobLog.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for log in logs:
        video_title = None
        channel_name = None

        if log.video_fk:
            video = db.get(Video, log.video_fk)
            if video:
                video_title = video.title
        if log.channel_fk:
            channel = db.get(Channel, log.channel_fk)
            if channel:
                channel_name = channel.name

        items.append(
            ActivityItem(
                id=log.id,
                action=log.action,
                status=log.status,
                error_message=log.error_message,
                video_title=video_title,
                channel_name=channel_name,
                created_at=log.created_at,
            )
        )
    return items
