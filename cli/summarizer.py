#!/usr/bin/env python3
"""YouTube Video Summarizer - Run daily to get summaries of new videos."""

import os
import json
import re
import httpx
from datetime import datetime

# --- Config Loading ---

def load_config(config_path="config.txt"):
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
    channels = []
    with open(channels_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            channels.append(line)
    return channels

def load_seen_videos(path="seen_videos.json"):
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()

def save_seen_videos(seen, path="seen_videos.json"):
    with open(path, "w") as f:
        json.dump(sorted(seen), f, indent=2)

# --- Channel Resolution ---

def resolve_channel_id(url_or_id):
    url_or_id = url_or_id.strip()
    if re.match(r"^UC[\w-]{22}$", url_or_id):
        return url_or_id, url_or_id
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", url_or_id)
    if m:
        return m.group(1), m.group(1)
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

def fetch_latest_videos(channel_id, api_key=None, max_results=2):
    if api_key:
        params = {
            "key": api_key, "channelId": channel_id, "part": "snippet",
            "order": "date", "maxResults": max_results, "type": "video",
        }
        resp = httpx.get(f"{YOUTUBE_API_URL}/search", params=params, timeout=30)
        resp.raise_for_status()
        videos = []
        for item in resp.json().get("items", []):
            vid_id = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            if vid_id:
                videos.append({
                    "video_id": vid_id, "title": snippet.get("title", "Untitled"),
                    "published_at": snippet.get("publishedAt", ""),
                    "channel_name": snippet.get("channelTitle", channel_id),
                })
        return videos
    else:
        print("  WARNING: No YOUTUBE_API_KEY set. Using RSS feed (may fail).")
        import feedparser
        feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
        videos = []
        for entry in feed.entries[:max_results]:
            vid_id = entry.get("yt_videoid", "")
            if vid_id:
                videos.append({
                    "video_id": vid_id, "title": entry.get("title", "Untitled"),
                    "published_at": entry.get("published", ""),
                    "channel_name": feed.feed.get("title", channel_id),
                })
        return videos

# --- Transcript ---

def fetch_transcript(video_id):
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

SYSTEM_PROMPT = """You are a senior research analyst producing executive briefings from video transcripts. Your summaries must be so insight-dense that reading them is genuinely more efficient than watching the video.

Output a single JSON object with exactly two fields. No markdown, no code fences — ONLY valid JSON.

### "summary" (string)
Write 3-5 sentences as an executive briefing in two short paragraphs. NOT a book report.
- Paragraph 1: The single most important claim or finding, stated as a direct assertion. Follow with the strongest evidence — include specific names, numbers, studies, or data points from the transcript. Never write vague placeholders like "specific genes" or "certain studies" — use the actual terms mentioned.
- Paragraph 2: The "so what" — actionable implications, who this affects, and why it matters now. When listing practical recommendations, briefly distinguish between those with strong human evidence and those based on animal studies or the speaker's personal practice.

### "sections" (array of objects)
Each object has "timestamp" (M:SS or MM:SS), "title" (5-10 words), and "description" (2-4 sentences).

Rules:
1. Create 5-15 sections scaled to video length.
2. Prioritize by insight value, not equal time. A 30-second breakthrough claim deserves a section; a 5-minute tangent may not. Merge or omit filler segments.
3. Titles must name the INSIGHT, not the topic. Write "Fasting triggers cellular repair via autophagy" not "Discussion of fasting." Titles must not overstate — if the speaker says "reversed aging markers," do not write "doubled lifespan."
4. Every description must include at least one of: a specific claim with evidence, a data point, an actionable recommendation, a named example, a direct quote in quotation marks, or a surprising/contrarian take.
5. When the speaker references specific genes, compounds, researchers, tools, or studies by name, always include those names — never use vague references.

Content type adaptation (auto-detect):
- Interview/Podcast: Lead with the guest's strongest claims. Capture disagreements between speakers. Preserve memorable phrasing in quotes.
- Tutorial: Name specific tools, versions, settings, commands. Flag common mistakes warned about.
- Lecture/Analysis: Trace the logical chain from evidence to conclusion. Capture frameworks or mental models introduced.
- News/Commentary: Separate reported facts from interpretation. Capture predictions with stated timeframes.

Quality check before output: Could someone who never watched this video make a specific decision, take concrete action, or accurately brief a colleague based solely on your summary? If not, replace vague language with specifics from the transcript."""

def parse_json_response(text):
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text)

def summarize_with_claude(transcript, video_title, api_key, model="claude-opus-4-6"):
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    max_chars = 400000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[transcript truncated]"
    for attempt in range(3):
        resp = client.messages.create(
            model=model, max_tokens=4096, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Video title: {video_title}\n\nTranscript:\n{transcript}"}],
        )
        try:
            return parse_json_response(resp.content[0].text)
        except json.JSONDecodeError:
            if attempt == 2:
                raise ValueError(f"Failed to parse JSON after 3 attempts. Raw response: {resp.content[0].text[:300]}")

def summarize_with_groq(transcript, video_title, api_key, model="llama-3.3-70b-versatile"):
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
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
    return parse_json_response(resp.choices[0].message.content)

def summarize(transcript, video_title, config):
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

# --- PDF Generation (one per channel, multiple videos) ---

def _timestamp_to_seconds(ts):
    """Convert M:SS or MM:SS to total seconds."""
    try:
        parts = ts.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return 0

def generate_channel_pdf(channel_name, video_summaries, output_dir="./pdfs"):
    """Generate a single PDF with all video summaries for a channel."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.colors import HexColor

    day_dir = os.path.join(output_dir, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(day_dir, exist_ok=True)
    safe_name = re.sub(r'[^\w\s-]', '', channel_name)[:40].strip()
    filename = f"{safe_name}.pdf"
    filepath = os.path.join(day_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()

    def esc(text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    channel_title_style = ParagraphStyle('CT', parent=styles['Heading1'], fontSize=22, spaceAfter=12)
    video_title_style = ParagraphStyle('VT', parent=styles['Heading1'], fontSize=16, spaceAfter=4)
    meta_style = ParagraphStyle('M', parent=styles['Normal'], fontSize=10, textColor=HexColor('#666666'))
    section_style = ParagraphStyle('S', parent=styles['Heading3'], fontSize=12, spaceBefore=10)
    footer_style = ParagraphStyle('F', parent=styles['Normal'], fontSize=8, textColor=HexColor('#999999'))

    elements = []

    # Channel header
    elements.append(Paragraph(esc(channel_name), channel_title_style))
    elements.append(Paragraph(f"Video Summaries — {datetime.now().strftime('%B %d, %Y')}", meta_style))
    elements.append(Spacer(1, 20))

    for i, vs in enumerate(video_summaries):
        if i > 0:
            elements.append(PageBreak())

        title = vs["title"]
        url = vs["url"]
        result = vs["result"]

        # Video title
        elements.append(Paragraph(esc(title), video_title_style))
        elements.append(Paragraph(f"<link href='{url}'>{esc(url)}</link>", meta_style))
        elements.append(Spacer(1, 8))

        # Summary
        elements.append(Paragraph("<b>Summary</b>", styles['Heading2']))
        elements.append(Paragraph(esc(result.get("summary", "")), styles['BodyText']))
        elements.append(Spacer(1, 8))

        # Sections
        sections = result.get("sections", [])
        if sections:
            elements.append(Paragraph("<b>Timestamps</b>", styles['Heading2']))
            for sec in sections:
                ts = sec.get("timestamp", "")
                stitle = sec.get("title", "")
                desc = sec.get("description", "")
                # Convert timestamp to seconds for YouTube link
                ts_seconds = _timestamp_to_seconds(ts)
                ts_url = f"{url}&t={ts_seconds}" if ts_seconds > 0 else url
                elements.append(Paragraph(f"<b><link href='{ts_url}'>{esc(ts)}</link> — {esc(stitle)}</b>", section_style))
                elements.append(Paragraph(esc(desc), styles['BodyText']))

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(f"Generated by YT Summarizer on {datetime.now().strftime('%Y-%m-%d %H:%M')}", footer_style))

    doc.build(elements)
    return filepath

# --- Email (single combined email) ---

def send_combined_email(config, all_results, pdf_paths):
    """Send one email with all channel summaries and PDFs attached."""
    import resend

    api_key = config.get("RESEND_API_KEY", "").strip()
    if not api_key:
        print("\nNo RESEND_API_KEY set, skipping email.")
        return

    sender = config.get("SENDER_EMAIL", "onboarding@resend.dev").strip()
    recipients = [e.strip() for e in config.get("RECIPIENTS", "").split(",") if e.strip()]
    if not recipients:
        print("\nNo RECIPIENTS set, skipping email.")
        return

    resend.api_key = api_key

    # Build email body
    body_lines = ["Daily YouTube Video Summaries", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

    for channel_name, videos in all_results.items():
        body_lines.append(f"--- {channel_name} ---")
        for v in videos:
            body_lines.append(f"\n> {v['title']}")
            body_lines.append(f"  {v['url']}")
            body_lines.append(f"  {v['result']['summary']}")
        body_lines.append("")

    body_lines.append("Full timestamped summaries attached as PDFs.")

    # Attach all PDFs
    attachments = []
    for pdf_path in pdf_paths:
        if os.path.isfile(pdf_path):
            with open(pdf_path, "rb") as f:
                attachments.append({"filename": os.path.basename(pdf_path), "content": list(f.read())})

    params = {
        "from": sender,
        "to": recipients,
        "subject": f"[YT Summary] Daily Digest — {datetime.now().strftime('%b %d, %Y')}",
        "text": "\n".join(body_lines),
    }
    if attachments:
        params["attachments"] = attachments

    resend.Emails.send(params)
    print(f"\nEmail sent to: {', '.join(recipients)}")

# --- Main ---

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("=" * 60)
    print("YouTube Video Summarizer")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    config = load_config("config.txt")
    channels = load_channels("channels.txt")
    seen_videos = load_seen_videos("seen_videos.json")

    if not channels:
        print("\nNo channels in channels.txt. Add some and run again.")
        return

    youtube_api_key = config.get("YOUTUBE_API_KEY", "").strip() or None
    pdf_dir = config.get("PDF_DIR", "./pdfs").strip()

    all_results = {}  # channel_name -> list of {title, url, result}
    all_pdfs = []
    total_new = 0
    total_processed = 0

    for channel_input in channels:
        print(f"\n{'─' * 50}")
        try:
            channel_id, channel_name = resolve_channel_id(channel_input)
            print(f"Channel: {channel_name}")
        except Exception as e:
            print(f"SKIP: Cannot resolve '{channel_input}': {e}")
            continue

        try:
            videos = fetch_latest_videos(channel_id, youtube_api_key, max_results=2)
            print(f"  Checking latest {len(videos)} videos...")
        except Exception as e:
            print(f"  SKIP: Cannot fetch videos: {e}")
            continue

        new_videos = [v for v in videos if v["video_id"] not in seen_videos]
        if not new_videos:
            print("  No new videos.")
            continue

        print(f"  {len(new_videos)} new video(s):")
        total_new += len(new_videos)
        channel_summaries = []

        for video in new_videos:
            vid_id = video["video_id"]
            title = video["title"]
            url = f"https://youtube.com/watch?v={vid_id}"
            print(f"\n    > {title}")

            # Transcript
            print(f"      Fetching transcript...")
            try:
                transcript = fetch_transcript(vid_id)
                print(f"      Got {len(transcript)} chars")
            except Exception as e:
                print(f"      FAILED (transcript): {e}")
                continue

            # Summarize
            print(f"      Summarizing...")
            try:
                result = summarize(transcript, title, config)
                print(f"      {len(result.get('sections', []))} sections")
            except Exception as e:
                print(f"      FAILED (summarize): {e}")
                continue

            channel_summaries.append({"title": title, "url": url, "result": result})
            seen_videos.add(vid_id)
            save_seen_videos(seen_videos)
            total_processed += 1

        # Generate one PDF per channel
        if channel_summaries:
            print(f"\n    Generating PDF for {channel_name}...")
            try:
                pdf_path = generate_channel_pdf(channel_name, channel_summaries, pdf_dir)
                all_pdfs.append(pdf_path)
                print(f"    PDF: {pdf_path}")
            except Exception as e:
                print(f"    PDF failed: {e}")

            all_results[channel_name] = channel_summaries

    # Send one combined email
    if all_results:
        print(f"\n{'─' * 50}")
        print("Sending daily digest email...")
        try:
            send_combined_email(config, all_results, all_pdfs)
        except Exception as e:
            print(f"Email failed: {e}")

    print(f"\n{'=' * 60}")
    print(f"Done! Processed {total_processed}/{total_new} new videos.")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
