import json
from openai import OpenAI
from app.services.llm.base import LLMProvider

DEFAULT_SYSTEM_PROMPT = """You are a video summarizer. Given a transcript with timestamps, produce a JSON object with:
- "summary": A 2-3 sentence overview of the video
- "sections": An array of objects, each with "timestamp" (MM:SS format), "title" (short section title), and "description" (2-3 sentence summary of that segment)

Identify natural topic boundaries. Output ONLY valid JSON, no markdown."""


class GrokProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.groq.com/openai/v1",
                 model: str = "llama-3.3-70b-versatile", system_prompt: str = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def summarize(self, transcript: str, video_title: str) -> dict:
        max_retries = 3
        for attempt in range(max_retries):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Video title: {video_title}\n\nTranscript:\n{transcript}"},
                ],
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to parse JSON after {max_retries} attempts: {content[:200]}")
