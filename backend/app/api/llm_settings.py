from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LLMConfig
from app.schemas import LLMConfigUpdate
from app.services.emailer import encrypt_password

router = APIRouter(prefix="/api/llm", tags=["llm"])

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL_GROQ = "llama-3.3-70b-versatile"
DEFAULT_MODEL_CLAUDE = "claude-opus-4-6"
DEFAULT_PROMPT = """You are an expert video summarizer that creates comprehensive, well-structured summaries.

Given a video transcript with timestamps, analyze the content and produce a JSON object with two fields:

1. "summary": A concise 3-5 sentence overview that captures the video's core thesis, key arguments, and main conclusions. Focus on WHY the content matters, not just WHAT is discussed. Include the speaker's main claim or finding if applicable.

2. "sections": An array of timestamped sections that break the video into logical chapters. Each section has:
   - "timestamp": The start time in M:SS or MM:SS format (e.g., "0:00", "12:35")
   - "title": A clear, descriptive title (5-10 words) that tells the reader what this section covers
   - "description": A 2-4 sentence summary capturing the key points, arguments, data, or stories presented in this segment. Include specific details like names, numbers, or findings mentioned — not vague generalizations.

Guidelines:
- Create 5-15 sections depending on video length (roughly one section per 3-5 minutes of content)
- Use the transcript timestamps to determine accurate section start times
- Each section should cover a distinct topic or shift in discussion
- Descriptions should be information-dense: a reader should learn the key takeaways without watching the video
- For interviews/podcasts: capture both the questions and the substantive answers
- For tutorials: capture the specific steps, tools, or techniques mentioned
- Avoid filler phrases like "the speaker discusses" — lead with the actual content

Output ONLY valid JSON. No markdown, no code fences, no extra text."""


@router.get("")
def get_llm_config(db: Session = Depends(get_db)):
    config = db.query(LLMConfig).first()
    if not config:
        return {
            "id": 0,
            "provider_type": "groq",
            "api_key": "",
            "base_url": DEFAULT_BASE_URL,
            "model_name": DEFAULT_MODEL_GROQ,
            "system_prompt": DEFAULT_PROMPT,
        }
    from app.main import settings
    from app.services.emailer import decrypt_password
    try:
        real_key = decrypt_password(config.api_key, settings.ENCRYPTION_KEY)
        masked = real_key[:4] + "****" + real_key[-4:] if len(real_key) > 8 else "******"
    except Exception:
        masked = "******"
    return {
        "id": config.id,
        "provider_type": config.provider_type,
        "api_key": masked,
        "base_url": config.base_url or "",
        "model_name": config.model_name,
        "system_prompt": config.system_prompt,
    }


@router.put("")
def update_llm_config(data: LLMConfigUpdate, db: Session = Depends(get_db)):
    from app.main import settings
    config = db.query(LLMConfig).first()
    encrypted_key = encrypt_password(data.api_key, settings.ENCRYPTION_KEY)
    if config:
        config.provider_type = data.provider_type
        config.api_key = encrypted_key
        config.base_url = data.base_url
        config.model_name = data.model_name
        config.system_prompt = data.system_prompt
    else:
        config = LLMConfig(
            provider_type=data.provider_type,
            api_key=encrypted_key,
            base_url=data.base_url,
            model_name=data.model_name,
            system_prompt=data.system_prompt,
        )
        db.add(config)
    db.commit()
    return {"status": "updated"}
