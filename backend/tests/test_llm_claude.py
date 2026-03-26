import json
from unittest.mock import patch, MagicMock
from app.services.llm.claude_provider import ClaudeProvider
from app.services.llm.factory import get_provider

VALID_RESPONSE = json.dumps({
    "summary": "Overview of the video.",
    "sections": [{"timestamp": "0:00", "title": "Intro", "description": "Desc"}]
})


@patch("app.services.llm.claude_provider.Anthropic")
def test_claude_summarize(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_block = MagicMock(text=VALID_RESPONSE)
    mock_client.messages.create.return_value = MagicMock(content=[mock_block])

    provider = ClaudeProvider(api_key="test-key")
    result = provider.summarize("transcript", "Title")
    assert result["summary"] == "Overview of the video."


def test_factory_returns_claude():
    settings = MagicMock(LLM_PROVIDER="claude", ANTHROPIC_API_KEY="key")
    provider = get_provider(settings)
    assert isinstance(provider, ClaudeProvider)
