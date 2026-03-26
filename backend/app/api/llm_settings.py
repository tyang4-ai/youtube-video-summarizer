import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LLMConfig
from app.schemas import LLMConfigUpdate, LLMConfigResponse
from app.services.emailer import encrypt_password

router = APIRouter(prefix="/api/llm", tags=["llm"])

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_PROMPT = """You are a video summarizer. Given a transcript with timestamps, produce a JSON object with:
- "summary": A 2-3 sentence overview of the video
- "sections": An array of objects, each with "timestamp" (MM:SS format), "title" (short section title), and "description" (2-3 sentence summary of that segment)

Identify natural topic boundaries. Output ONLY valid JSON, no markdown."""


@router.get("")
def get_llm_config(db: Session = Depends(get_db)):
    config = db.query(LLMConfig).first()
    if not config:
        return {
            "id": 0,
            "api_key": "",
            "base_url": DEFAULT_BASE_URL,
            "model_name": DEFAULT_MODEL,
            "system_prompt": DEFAULT_PROMPT,
        }
    # Decrypt to mask display
    from app.main import settings
    from app.services.emailer import decrypt_password
    try:
        real_key = decrypt_password(config.api_key, settings.ENCRYPTION_KEY)
        masked = real_key[:4] + "****" + real_key[-4:] if len(real_key) > 8 else "******"
    except Exception:
        masked = "******"
    return {
        "id": config.id,
        "api_key": masked,
        "base_url": config.base_url,
        "model_name": config.model_name,
        "system_prompt": config.system_prompt,
    }


@router.put("")
def update_llm_config(data: LLMConfigUpdate, db: Session = Depends(get_db)):
    from app.main import settings
    config = db.query(LLMConfig).first()
    # Encrypt the API key
    from app.services.emailer import encrypt_password
    encrypted_key = encrypt_password(data.api_key, settings.ENCRYPTION_KEY)
    if config:
        config.api_key = encrypted_key
        config.base_url = data.base_url
        config.model_name = data.model_name
        config.system_prompt = data.system_prompt
    else:
        config = LLMConfig(
            api_key=encrypted_key,
            base_url=data.base_url,
            model_name=data.model_name,
            system_prompt=data.system_prompt,
        )
        db.add(config)
    db.commit()
    return {"status": "updated"}
