import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EmailConfig
from app.schemas import EmailConfigUpdate, EmailConfigResponse

router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("", response_model=EmailConfigResponse | None)
def get_email_config(db: Session = Depends(get_db)):
    config = db.query(EmailConfig).first()
    if not config:
        return None

    recipients = json.loads(config.recipients_json)
    return EmailConfigResponse(
        id=config.id,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_password=config.smtp_password,
        sender_email=config.sender_email,
        recipients=recipients,
        is_active=config.is_active,
    )


@router.put("", response_model=EmailConfigResponse)
def upsert_email_config(
    payload: EmailConfigUpdate, db: Session = Depends(get_db)
):
    from app.main import settings
    from app.services.emailer import encrypt_password

    config = db.query(EmailConfig).first()
    encrypted = encrypt_password(payload.smtp_password, settings.ENCRYPTION_KEY)

    if config:
        config.smtp_host = payload.smtp_host
        config.smtp_port = payload.smtp_port
        config.smtp_user = payload.smtp_user
        config.smtp_password = encrypted
        config.sender_email = payload.sender_email
        config.recipients_json = json.dumps(payload.recipients)
        config.is_active = payload.is_active
    else:
        config = EmailConfig(
            smtp_host=payload.smtp_host,
            smtp_port=payload.smtp_port,
            smtp_user=payload.smtp_user,
            smtp_password=encrypted,
            sender_email=payload.sender_email,
            recipients_json=json.dumps(payload.recipients),
            is_active=payload.is_active,
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    recipients = json.loads(config.recipients_json)
    return EmailConfigResponse(
        id=config.id,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_password=config.smtp_password,
        sender_email=config.sender_email,
        recipients=recipients,
        is_active=config.is_active,
    )


@router.post("/test", status_code=200)
def test_email(db: Session = Depends(get_db)):
    from app.main import settings
    from app.services.emailer import decrypt_password, send_summary_email

    config = db.query(EmailConfig).first()
    if not config:
        raise HTTPException(status_code=404, detail="No email config found")

    try:
        recipients = json.loads(config.recipients_json)
        password = decrypt_password(config.smtp_password, settings.ENCRYPTION_KEY)
        send_summary_email(
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=password,
            sender_email=config.sender_email,
            recipients=recipients,
            video_title="Test Video",
            channel_name="Test Channel",
            summary_text="This is a test email from YT Summarizer.",
            video_url="https://youtube.com/watch?v=test",
            pdf_path="",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email test failed: {e}")

    return {"detail": "Test email sent successfully"}
