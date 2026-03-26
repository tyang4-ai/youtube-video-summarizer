import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import EmailConfig
from app.schemas import EmailConfigUpdate
from app.services.emailer import encrypt_password, send_summary_email

router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("")
def get_email_config(db: Session = Depends(get_db)):
    config = db.query(EmailConfig).first()
    if not config:
        return None
    from app.main import settings
    from app.services.emailer import decrypt_password
    try:
        real_key = decrypt_password(config.resend_api_key, settings.ENCRYPTION_KEY)
        masked = real_key[:4] + "****" + real_key[-4:] if len(real_key) > 8 else "******"
    except Exception:
        masked = "******"
    return {
        "id": config.id,
        "resend_api_key": masked,
        "sender_email": config.sender_email,
        "recipients": json.loads(config.recipients_json),
        "is_active": config.is_active,
    }


@router.put("")
def update_email_config(data: EmailConfigUpdate, db: Session = Depends(get_db)):
    from app.main import settings
    config = db.query(EmailConfig).first()
    encrypted_key = encrypt_password(data.resend_api_key, settings.ENCRYPTION_KEY)
    if config:
        config.resend_api_key = encrypted_key
        config.sender_email = data.sender_email
        config.recipients_json = json.dumps(data.recipients)
        config.is_active = data.is_active
    else:
        config = EmailConfig(
            resend_api_key=encrypted_key,
            sender_email=data.sender_email,
            recipients_json=json.dumps(data.recipients),
            is_active=data.is_active,
        )
        db.add(config)
    db.commit()
    return {"status": "updated"}


@router.post("/test")
def send_test_email(db: Session = Depends(get_db)):
    from app.main import settings
    from app.services.emailer import decrypt_password
    config = db.query(EmailConfig).first()
    if not config:
        raise HTTPException(status_code=400, detail="Email not configured")
    recipients = json.loads(config.recipients_json)
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients configured")
    api_key = decrypt_password(config.resend_api_key, settings.ENCRYPTION_KEY)
    send_summary_email(
        resend_api_key=api_key,
        sender_email=config.sender_email,
        recipients=[recipients[0]],
        video_title="Test Email",
        channel_name="YT Summarizer",
        summary_text="This is a test email from YT Summarizer.",
        video_url="https://youtube.com",
        pdf_path="",
    )
    return {"status": "test email sent"}
