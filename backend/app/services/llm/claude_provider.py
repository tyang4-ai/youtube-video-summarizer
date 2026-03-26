import json
from anthropic import Anthropic
from app.services.llm.base import LLMProvider

DEFAULT_SYSTEM_PROMPT = """You are an expert video summarizer that creates comprehensive, well-structured summaries.

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
