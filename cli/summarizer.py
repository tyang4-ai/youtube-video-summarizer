#!/usr/bin/env python3
"""YouTube Video Summarizer - Run daily to get summaries of new videos."""

import os
import sys
import json
import re
import httpx
from pathlib import Path
from datetime import datetime

# --- Config Loading ---

def load_config(config_path="config.txt"):
    """Load key=value config from text file."""
    config = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config

def load_channels(channels_path="channels.txt"):
    """Load channel URLs/IDs from text file."""
    channels = []
    with open(channels_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            channels.append(line)
    return channels

def load_seen_videos(path="seen_videos.json"):
    """Load set of already-processed video IDs."""
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()

def save_seen_videos(seen, path="seen_videos.json"):
    """Save processed video IDs."""
    with open(path, "w") as f:
        json.dump(sorted(seen), f, indent=2)

# --- Channel Resolution ---

def resolve_channel_id(url_or_id):
    """Extract YouTube channel ID from various URL formats."""
    url_or_id = url_or_id.strip()

    # Raw channel ID
    if re.match(r"^UC[\w-]{22}$", url_or_id):
        return url_or_id, url_or_id

    # /channel/UCxxxx URL
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", url_or_id)
    if m:
        return m.group(1), m.group(1)

    # /@handle or /c/name URL - fetch page to find channel ID
    if re.search(r"youtube\.com/(@[\w.-]+|c/[\w.-]+)", url_or_id):
        resp = httpx.get(url_or_id, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        m = re.search(r'"channelId":"(UC[\w-]+)"', resp.text)
        if m:
            name_match = re.search(r'<meta property="og:title" content="([^"]+)"', resp.text)
            name = name_match.group(1) if name_match else m.group(1)
            return m.group(1), name

    raise ValueError(f"Cannot resolve channel from: {url_or_id}")

# --- YouTube API ---

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"

def fetch_latest_videos(channel_id, api_key=None, max_results=5):
    """Fetch latest videos from a channel. Uses YouTube Data API if key available, else yt-dlp."""
    if api_key:
        params = {
            "key": api_key,
            "channelId": channel_id,
            "part": "snippet",
            "order": "date",
            "maxResults": max_results,
            "type": "video",
        }
        resp = httpx.get(f"{YOUTUBE_API_URL}/search", params=params, timeout=30)
        resp.raise_for_status()
        videos = []
        for item in resp.json().get("items", []):
            vid_id = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            if vid_id:
                videos.append({
                    "video_id": vid_id,
                    "title": snippet.get("title", "Untitled"),
                    "published_at": snippet.get("publishedAt", ""),
                    "channel_name": snippet.get("channelTitle", channel_id),
                })
        return videos
    else:
        # Fallback: no API key, try RSS (may not work)
        print("  WARNING: No YOUTUBE_API_KEY set. Using RSS feed (may fail).")
        import feedparser
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(url)
        videos = []
        for entry in feed.entries[:max_results]:
            vid_id = entry.get("yt_videoid", "")
            if vid_id:
                videos.append({
                    "video_id": vid_id,
                    "title": entry.get("title", "Untitled"),
                    "published_at": entry.get("published", ""),
                    "channel_name": feed.feed.get("title", channel_id),
                })
        return videos

# --- Transcript ---

def fetch_transcript(video_id):
    """Fetch transcript using youtube-transcript-api."""
    from youtube_transcript_api import YouTubeTranscriptApi

    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch(video_id, languages=["en"])

    lines = []
    for snippet in transcript:
        m, s = divmod(int(snippet.start), 60)
        text = snippet.text.strip()
        if text:
            lines.append(f"[{m}:{s:02d}] {text}")

    if not lines:
        raise Exception(f"Empty transcript for {video_id}")

    return "\n".join(lines)

# --- LLM Summarization ---

SYSTEM_PROMPT = """You are an expert video summarizer that creates comprehensive, well-structured summaries.

Given a video transcript with timestamps, analyze the content and produce a JSON object with two fields:

1. "summary": A concise 3-5 sentence overview that captures the video's core thesis, key arguments, and main conclusions. Focus on WHY the content matters, not just WHAT is discussed.

2. "sections": An array of timestamped sections that break the video into logical chapters. Each section has:
   - "timestamp": The start time in M:SS or MM:SS format
   - "title": A clear, descriptive title (5-10 words)
   - "description": A 2-4 sentence summary with specific details, names, numbers, or findings.

Guidelines:
- Create 5-15 sections depending on video length
- Descriptions should be information-dense
- For interviews: capture both questions and answers
- For tutorials: capture steps and tools
- Avoid filler phrases like "the speaker discusses"

Output ONLY valid JSON. No markdown, no code fences."""

def summarize_with_claude(transcript, video_title, api_key, model="claude-opus-4-6"):
    """Summarize using Claude API."""
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    # Chunk if needed (Claude has 200K context but let's be safe)
    max_chars = 400000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[transcript truncated]"

    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Video title: {video_title}\n\nTranscript:\n{transcript}"}],
    )
    return json.loads(resp.content[0].text)

def summarize_with_groq(transcript, video_title, api_key, model="llama-3.3-70b-versatile"):
    """Summarize using Groq API (OpenAI-compatible)."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    # Groq has 8K token limit on free tier, chunk aggressively
    max_chars = 28000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[transcript truncated]"

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Video title: {video_title}\n\nTranscript:\n{transcript}"},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)

def summarize(transcript, video_title, config):
    """Route to the right LLM provider."""
    provider = config.get("LLM_PROVIDER", "claude").lower()
    model = config.get("MODEL", "").strip()

    if provider == "claude":
        api_key = config.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in config.txt")
        return summarize_with_claude(transcript, video_title, api_key, model or "claude-opus-4-6")
    elif provider == "groq":
        api_key = config.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in config.txt")
        return summarize_with_groq(transcript, video_title, api_key, model or "llama-3.3-70b-versatile")
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

# --- PDF Generation ---

def generate_pdf(video_title, channel_name, video_url, summary_data, output_dir="./pdfs"):
    """Generate a formatted PDF summary."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.colors import HexColor

    os.makedirs(output_dir, exist_ok=True)
    safe_title = re.sub(r'[^\w\s-]', '', video_title)[:50].strip()
    filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()

    def esc(text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    elements = []

    # Header
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=18, spaceAfter=6)
    meta_style = ParagraphStyle('M', parent=styles['Normal'], fontSize=10, textColor=HexColor('#666666'))
    elements.append(Paragraph(esc(video_title), title_style))
    elements.append(Paragraph(f"{esc(channel_name)} | {datetime.now().strftime('%B %d, %Y')}", meta_style))
    elements.append(Paragraph(f"<link href='{video_url}'>{esc(video_url)}</link>", meta_style))
    elements.append(Spacer(1, 12))

    # Summary
    elements.append(Paragraph("<b>Summary</b>", styles['Heading2']))
    elements.append(Paragraph(esc(summary_data.get("summary", "")), styles['BodyText']))
    elements.append(Spacer(1, 12))

    # Sections
    sections = summary_data.get("sections", [])
    if sections:
        elements.append(Paragraph("<b>Timestamps</b>", styles['Heading2']))
        section_style = ParagraphStyle('S', parent=styles['Heading2'], fontSize=14, spaceBefore=12)
        for sec in sections:
            ts = sec.get("timestamp", "")
            title = sec.get("title", "")
            desc = sec.get("description", "")
            elements.append(Paragraph(f"<b>{esc(ts)} — {esc(title)}</b>", section_style))
            elements.append(Paragraph(esc(desc), styles['BodyText']))

    # Footer
    elements.append(Spacer(1, 24))
    footer_style = ParagraphStyle('F', parent=styles['Normal'], fontSize=8, textColor=HexColor('#999999'))
    elements.append(Paragraph(f"Generated by YT Summarizer on {datetime.now().strftime('%Y-%m-%d %H:%M')}", footer_style))

    doc.build(elements)
    return filepath

# --- Email ---

def send_email(config, video_title, channel_name, summary_text, video_url, pdf_path):
    """Send summary email via Resend."""
    import resend

    api_key = config.get("RESEND_API_KEY", "").strip()
    if not api_key:
        print("  No RESEND_API_KEY set, skipping email.")
        return

    sender = config.get("SENDER_EMAIL", "onboarding@resend.dev").strip()
    recipients = [e.strip() for e in config.get("RECIPIENTS", "").split(",") if e.strip()]
    if not recipients:
        print("  No RECIPIENTS set, skipping email.")
        return

    resend.api_key = api_key

    params = {
        "from": sender,
        "to": recipients,
        "subject": f"[YT Summary] {video_title} — {channel_name}",
        "text": f"New video summary!\n\nVideo: {video_title}\nChannel: {channel_name}\nLink: {video_url}\n\nSummary:\n{summary_text}\n\nFull timestamped summary attached as PDF.",
    }

    if pdf_path and os.path.isfile(pdf_path):
        with open(pdf_path, "rb") as f:
            params["attachments"] = [{"filename": os.path.basename(pdf_path), "content": list(f.read())}]

    resend.Emails.send(params)
    print(f"  Email sent to: {', '.join(recipients)}")

# --- Main ---

def process_video(video, config, seen_videos):
    """Process a single video: transcript -> summarize -> PDF -> email."""
    vid_id = video["video_id"]
    title = video["title"]
    channel = video.get("channel_name", "Unknown")
    url = f"https://youtube.com/watch?v={vid_id}"

    print(f"\n  Processing: {title}")

    # Fetch transcript
    print(f"    Fetching transcript...")
    try:
        transcript = fetch_transcript(vid_id)
        print(f"    Got {len(transcript)} chars")
    except Exception as e:
        print(f"    FAILED (transcript): {e}")
        return False

    # Summarize
    print(f"    Summarizing with {config.get('LLM_PROVIDER', 'claude')}...")
    try:
        result = summarize(transcript, title, config)
        print(f"    Summary: {result['summary'][:100]}...")
        print(f"    Sections: {len(result.get('sections', []))}")
    except Exception as e:
        print(f"    FAILED (summarize): {e}")
        return False

    # Generate PDF
    pdf_dir = config.get("PDF_DIR", "./pdfs").strip()
    print(f"    Generating PDF...")
    try:
        pdf_path = generate_pdf(title, channel, url, result, pdf_dir)
        print(f"    PDF: {pdf_path}")
    except Exception as e:
        print(f"    FAILED (PDF): {e}")
        return False

    # Send email
    try:
        send_email(config, title, channel, result["summary"], url, pdf_path)
    except Exception as e:
        print(f"    Email failed: {e}")

    # Mark as seen
    seen_videos.add(vid_id)
    return True

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("=" * 60)
    print("YouTube Video Summarizer")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load config
    config = load_config("config.txt")
    channels = load_channels("channels.txt")
    seen_videos = load_seen_videos("seen_videos.json")

    if not channels:
        print("\nNo channels in channels.txt. Add some and run again.")
        return

    youtube_api_key = config.get("YOUTUBE_API_KEY", "").strip() or None

    total_new = 0
    total_processed = 0

    for channel_input in channels:
        print(f"\n{'─' * 50}")
        # Resolve channel
        try:
            channel_id, channel_name = resolve_channel_id(channel_input)
            print(f"Channel: {channel_name} ({channel_id})")
        except Exception as e:
            print(f"SKIP: Cannot resolve '{channel_input}': {e}")
            continue

        # Fetch latest videos
        try:
            videos = fetch_latest_videos(channel_id, youtube_api_key)
            print(f"Found {len(videos)} recent videos")
        except Exception as e:
            print(f"SKIP: Cannot fetch videos: {e}")
            continue

        # Filter to unseen
        new_videos = [v for v in videos if v["video_id"] not in seen_videos]
        if not new_videos:
            print("No new videos.")
            continue

        print(f"{len(new_videos)} new video(s) to process:")
        total_new += len(new_videos)

        for video in new_videos:
            if process_video(video, config, seen_videos):
                total_processed += 1
            # Save after each video in case of crash
            save_seen_videos(seen_videos)

    print(f"\n{'=' * 60}")
    print(f"Done! Processed {total_processed}/{total_new} new videos.")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
