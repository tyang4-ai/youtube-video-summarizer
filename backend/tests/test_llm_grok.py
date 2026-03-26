import json
from unittest.mock import patch, MagicMock
import pytest
from app.services.llm.grok_provider import GrokProvider
from app.services.llm.factory import get_provider


VALID_RESPONSE = json.dumps({
    "summary": "This video covers Python basics.",
    "sections": [
        {"timestamp": "0:00", "title": "Intro", "description": "The host introduces the topic."}
    ]
})


@patch("app.services.llm.grok_provider.OpenAI")
def test_grok_summarize_returns_parsed_json(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_msg = MagicMock()
    mock_msg.content = VALID_RESPONSE
    mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=mock_msg)])

    provider = GrokProvider(api_key="test-key")
    result = provider.summarize("transcript text", "Test Video")
    assert result["summary"] == "This video covers Python basics."
    assert len(result["sections"]) == 1


@patch("app.services.llm.grok_provider.OpenAI")
def test_grok_retries_on_malformed_json(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    bad_msg = MagicMock(content="not json")
    good_msg = MagicMock(content=VALID_RESPONSE)
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=bad_msg)]),
        MagicMock(choices=[MagicMock(message=good_msg)]),
    ]

    provider = GrokProvider(api_key="test-key")
    result = provider.summarize("transcript", "Title")
    assert "summary" in result


def test_factory_returns_grok():
    settings = MagicMock(LLM_PROVIDER="grok", XAI_API_KEY="key")
    provider = get_provider(settings)
    assert isinstance(provider, GrokProvider)
