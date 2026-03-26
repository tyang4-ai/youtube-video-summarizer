from app.config import Settings


def test_default_settings():
    s = Settings(XAI_API_KEY="test-key", ENCRYPTION_KEY="test-enc-key")
    assert s.LLM_PROVIDER == "grok"
    assert s.DATABASE_URL == "sqlite:///./data/yt_summarizer.db"
    assert s.PDF_DIR == "./data/pdfs"
    assert s.HOST == "0.0.0.0"
    assert s.PORT == 8000


def test_llm_provider_accepts_claude():
    s = Settings(
        LLM_PROVIDER="claude",
        ANTHROPIC_API_KEY="test-key",
        ENCRYPTION_KEY="test-enc-key",
    )
    assert s.LLM_PROVIDER == "claude"
