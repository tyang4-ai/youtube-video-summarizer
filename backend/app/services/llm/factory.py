from app.services.llm.base import LLMProvider
from app.services.llm.grok_provider import GrokProvider


def get_provider(settings) -> LLMProvider:
    if settings.LLM_PROVIDER == "grok":
        return GrokProvider(api_key=settings.XAI_API_KEY)
    elif settings.LLM_PROVIDER == "claude":
        from app.services.llm.claude_provider import ClaudeProvider
        return ClaudeProvider(api_key=settings.ANTHROPIC_API_KEY)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
