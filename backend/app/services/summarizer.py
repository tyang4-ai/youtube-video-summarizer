from app.services.llm.base import LLMProvider

DEFAULT_MAX_TOKENS = 120000  # Conservative for Grok's 131K window


def summarize_transcript(
    transcript: str,
    video_title: str,
    provider: LLMProvider,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict:
    estimated_tokens = len(transcript) // 4
    if estimated_tokens <= max_tokens:
        return provider.summarize(transcript, video_title)

    # Chunk by timestamp boundaries
    chunks = _split_by_timestamps(transcript, max_tokens)
    chunk_results = []
    for chunk in chunks:
        result = provider.summarize(chunk, video_title)
        chunk_results.append(result)

    # Merge pass
    return _merge_summaries(chunk_results, video_title, provider)


def _split_by_timestamps(transcript: str, max_tokens: int) -> list[str]:
    lines = transcript.split("\n")
    chunks = []
    current_chunk = []
    current_size = 0
    chunk_limit = max_tokens * 4  # Convert back to chars

    for line in lines:
        line_size = len(line)
        if current_size + line_size > chunk_limit and current_chunk:
            chunks.append("\n".join(current_chunk))
            # Keep last 10% as overlap
            overlap_count = max(1, len(current_chunk) // 10)
            current_chunk = current_chunk[-overlap_count:]
            current_size = sum(len(l) for l in current_chunk)
        current_chunk.append(line)
        current_size += line_size

    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks


def _merge_summaries(chunk_results: list[dict], video_title: str, provider: LLMProvider) -> dict:
    all_sections = []
    for cr in chunk_results:
        all_sections.extend(cr.get("sections", []))

    summaries_text = "\n".join(cr.get("summary", "") for cr in chunk_results)
    merge_input = f"Combine these partial summaries into one cohesive summary:\n{summaries_text}"
    merged = provider.summarize(merge_input, video_title)
    merged["sections"] = all_sections
    return merged
