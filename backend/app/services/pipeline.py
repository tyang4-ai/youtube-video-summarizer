import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Channel, Video, Summary, EmailConfig
from app.services.poller import poll_channel
from app.services.transcriber import get_transcript, TranscriptUnavailableError
from app.services.summarizer import summarize_transcript
from app.services.pdf_generator import generate_pdf
from app.services.emailer import send_summary_email, decrypt_password
from app.services.job_logger import log_job

logger = logging.getLogger(__name__)


def process_channel(channel_id: int, db: Session, settings, provider) -> None:
    channel = db.get(Channel, channel_id)
    if not channel:
        return

    known_ids = {v.youtube_video_id for v in db.query(Video.youtube_video_id).filter_by(channel_fk=channel_id)}
    try:
        new_videos = poll_channel(channel.youtube_channel_id, known_ids)
        log_job(db, "poll", "success", channel_id=channel_id)
    except Exception as e:
        log_job(db, "poll", "failed", channel_id=channel_id, error=str(e))
        logger.error(f"Poll failed for channel {channel_id}: {e}")
        return

    channel.last_polled_at = datetime.utcnow()
    db.commit()

    for vdata in new_videos:
        vid = Video(
            channel_fk=channel_id,
            youtube_video_id=vdata["video_id"],
            title=vdata["title"],
            published_at=vdata.get("published_at"),
            status="pending",
        )
        db.add(vid)
        db.commit()
        _process_video(vid, channel, db, settings, provider)


def _process_video(video: Video, channel: Channel, db: Session, settings, provider) -> None:
    # Fetch transcript
    try:
        transcript = get_transcript(video.youtube_video_id)
        video.transcript_text = transcript
        db.commit()
        log_job(db, "transcribe", "success", channel_id=channel.id, video_id=video.id)
    except TranscriptUnavailableError as e:
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        log_job(db, "transcribe", "failed", channel_id=channel.id, video_id=video.id, error=str(e))
        return

    # Summarize
    try:
        result = summarize_transcript(transcript, video.title, provider)
        log_job(db, "summarize", "success", channel_id=channel.id, video_id=video.id)
    except Exception as e:
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        log_job(db, "summarize", "failed", channel_id=channel.id, video_id=video.id, error=str(e))
        return

    # Generate PDF
    try:
        pdf_path = generate_pdf(
            video_title=video.title,
            channel_name=channel.name,
            published_at=video.published_at or datetime.utcnow(),
            video_url=f"https://youtube.com/watch?v={video.youtube_video_id}",
            summary=result["summary"],
            sections=result.get("sections", []),
            output_dir=settings.PDF_DIR,
        )
        log_job(db, "pdf", "success", channel_id=channel.id, video_id=video.id)
    except Exception as e:
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        log_job(db, "pdf", "failed", channel_id=channel.id, video_id=video.id, error=str(e))
        return

    # Save summary
    summary = Summary(
        video_id=video.id,
        summary_text=result["summary"],
        timestamps_json=json.dumps(result.get("sections", [])),
        pdf_path=pdf_path,
    )
    db.add(summary)
    video.status = "summarized"
    db.commit()

    # Send email
    send_email_for_video(video, channel, summary, result, db, settings)


def send_email_for_video(video, channel, summary, result, db, settings):
    email_config = db.query(EmailConfig).first()
    if not email_config or not email_config.is_active:
        return

    try:
        recipients = json.loads(email_config.recipients_json)
        password = decrypt_password(email_config.smtp_password, settings.ENCRYPTION_KEY)
        send_summary_email(
            smtp_host=email_config.smtp_host,
            smtp_port=email_config.smtp_port,
            smtp_user=email_config.smtp_user,
            smtp_password=password,
            sender_email=email_config.sender_email,
            recipients=recipients,
            video_title=video.title,
            channel_name=channel.name,
            summary_text=result["summary"],
            video_url=f"https://youtube.com/watch?v={video.youtube_video_id}",
            pdf_path=summary.pdf_path,
        )
        summary.email_sent = True
        db.commit()
        log_job(db, "email", "success", channel_id=channel.id, video_id=video.id)
    except Exception as e:
        log_job(db, "email", "failed", channel_id=channel.id, video_id=video.id, error=str(e))
        logger.error(f"Email failed for video {video.id}: {e}")
