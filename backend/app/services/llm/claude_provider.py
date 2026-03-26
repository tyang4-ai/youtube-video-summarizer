import json
from anthropic import Anthropic
from app.services.llm.base import LLMProvider

DEFAULT_SYSTEM_PROMPT = """You are a video summarizer. Given a transcript with timestamps, produce a JSON object with:
- "summary": A 2-3 sentence overview of the video
- "sections": An array of objects, each with "timestamp" (MM:SS format), "title" (short section title), and "description" (2-3 sentence summary of that segment)

Identify natural topic boundaries. Output ONLY valid JSON, no markdown."""


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-opus-4-6", system_prompt: str = None):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def summarize(self, transcript: str, video_title: str) -> dict:
        max_retries = 3
        for attempt in range(max_retries):
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": f"Video title: {video_title}\n\nTranscript:\n{transcript}"},
                ],
            )
            content = resp.content[0].text
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to parse JSON after {max_retries} attempts: {content[:200]}")
