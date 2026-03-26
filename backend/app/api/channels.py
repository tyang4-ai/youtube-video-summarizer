from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Channel
from app.schemas import ChannelCreate, ChannelUpdate, ChannelResponse
from app.services.channel_resolver import resolve_channel_id

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("", response_model=list[ChannelResponse])
def list_channels(db: Session = Depends(get_db)):
    return db.query(Channel).all()


@router.post("", response_model=ChannelResponse, status_code=201)
def add_channel(payload: ChannelCreate, db: Session = Depends(get_db)):
    from app.main import scheduler, settings, provider

    try:
        yt_channel_id, name = resolve_channel_id(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = db.query(Channel).filter_by(youtube_channel_id=yt_channel_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Channel already exists")

    channel = Channel(
        youtube_channel_id=yt_channel_id,
        name=name,
        url=payload.url,
        poll_interval_minutes=payload.poll_interval_minutes,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    from app.services.scheduler import register_channel_job
    from app.database import SessionLocal

    register_channel_job(scheduler, channel, SessionLocal, settings, provider)

    return channel


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(
    channel_id: int, payload: ChannelUpdate, db: Session = Depends(get_db)
):
    from app.main import scheduler, settings, provider

    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if payload.poll_interval_minutes is not None:
        channel.poll_interval_minutes = payload.poll_interval_minutes
    if payload.is_active is not None:
        channel.is_active = payload.is_active

    db.commit()
    db.refresh(channel)

    from app.services.scheduler import reschedule_channel_job
    from app.database import SessionLocal

    reschedule_channel_job(scheduler, channel, SessionLocal, settings, provider)

    return channel


@router.delete("/{channel_id}", status_code=204)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    from app.main import scheduler

    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    from app.services.scheduler import remove_channel_job

    try:
        remove_channel_job(scheduler, channel.id)
    except Exception:
        pass

    db.delete(channel)
    db.commit()
    return None


@router.post("/{channel_id}/poll", status_code=202)
def force_poll(
    channel_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from app.main import settings, provider

    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    from app.services.pipeline import process_channel
    from app.database import SessionLocal

    def _run():
        session = SessionLocal()
        try:
            process_channel(channel_id, session, settings, provider)
        finally:
            session.close()

    background_tasks.add_task(_run)
    return {"detail": "Poll started"}
