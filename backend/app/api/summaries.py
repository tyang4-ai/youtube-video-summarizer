import json

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models import Summary, Video, Channel, EmailConfig
from app.schemas import SummaryListItem, SummaryResponse

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.get("", response_model=list[SummaryListItem])
def list_summaries(channel_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Summary, Video, Channel).join(
        Video, Summary.video_id == Video.id
    ).join(
        Channel, Video.channel_fk == Channel.id
    )
    if channel_id is not None:
        query = query.filter(Video.channel_fk == channel_id)

    results = query.order_by(Summary.created_at.desc()).all()

    items = []
    for summary, video, channel in results:
        items.append(
            SummaryListItem(
                id=summary.id,
                video_id=summary.video_id,
                video_title=video.title,
                channel_name=channel.name,
                summary_text=summary.summary_text,
                email_sent=summary.email_sent,
                created_at=summary.created_at,
            )
        )
    return items


@router.get("/{summary_id}", response_model=SummaryResponse)
def get_summary(summary_id: int, db: Session = Depends(get_db)):
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    try:
        timestamps = json.loads(summary.timestamps_json)
    except (json.JSONDecodeError, TypeError):
        timestamps = []

    return SummaryResponse(
        id=summary.id,
        video_id=summary.video_id,
        summary_text=summary.summary_text,
        timestamps=timestamps,
        pdf_path=summary.pdf_path,
        email_sent=summary.email_sent,
        created_at=summary.created_at,
    )


@router.get("/{summary_id}/pdf")
def download_pdf(summary_id: int, db: Session = Depends(get_db)):
    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    if not summary.pdf_path:
        raise HTTPException(status_code=404, detail="No PDF available")

    pdf = Path(summary.pdf_path)
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        str(pdf), media_type="application/pdf", filename=pdf.name
    )


@router.post("/{summary_id}/resend", status_code=202)
def resend_email(
    summary_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from app.main import settings

    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    video = db.get(Video, summary.video_id)
    channel = db.get(Channel, video.channel_fk)

    from app.database import SessionLocal

    def _run():
        session = SessionLocal()
        try:
            from app.services.pipeline import send_email_for_video

            s = session.get(Summary, summary_id)
            v = session.get(Video, s.video_id)
            c = session.get(Channel, v.channel_fk)
            result = {"summary": s.summary_text}
            send_email_for_video(v, c, s, result, session, settings)
        finally:
            session.close()

    background_tasks.add_task(_run)
    return {"detail": "Email resend started"}


@router.post("/{summary_id}/regenerate", status_code=202)
def regenerate_summary(
    summary_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from app.main import settings, provider

    summary = db.get(Summary, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    video = db.get(Video, summary.video_id)
    if not video or not video.transcript_text:
        raise HTTPException(
            status_code=400, detail="No cached transcript available"
        )

    from app.database import SessionLocal

    def _run():
        session = SessionLocal()
        try:
            from app.services.summarizer import summarize_transcript
            from app.services.pdf_generator import generate_pdf
            from datetime import datetime

            v = session.get(Video, video.id)
            c = session.get(Channel, v.channel_fk)
            s = session.get(Summary, summary_id)

            result = summarize_transcript(v.transcript_text, v.title, provider)
            pdf_path = generate_pdf(
                video_title=v.title,
                channel_name=c.name,
                published_at=v.published_at or datetime.utcnow(),
                video_url=f"https://youtube.com/watch?v={v.youtube_video_id}",
                summary=result["summary"],
                sections=result.get("sections", []),
                output_dir=settings.PDF_DIR,
            )
            s.summary_text = result["summary"]
            s.timestamps_json = json.dumps(result.get("sections", []))
            s.pdf_path = pdf_path
            session.commit()
        finally:
            session.close()

    background_tasks.add_task(_run)
    return {"detail": "Regeneration started"}
