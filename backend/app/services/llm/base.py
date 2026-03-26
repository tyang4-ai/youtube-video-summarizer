from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def summarize(self, transcript: str, video_title: str) -> dict:
        """Returns {"summary": str, "sections": [{"timestamp", "title", "description"}]}"""
        pass
