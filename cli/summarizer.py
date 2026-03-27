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

def resolve_channel_id(url_or_id, api_key=None):
    url_or_id = url_or_id.strip()

    # Raw channel ID
    if re.match(r"^UC[\w-]{22}$", url_or_id):
        name = _get_channel_name(url_or_id, api_key) or url_or_id
        return url_or_id, name

    # /channel/UCxxxx URL
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", url_or_id)
    if m:
        cid = m.group(1)
        name = _get_channel_name(cid, api_key) or cid
        return cid, name

    # Bare @handle (e.g. "@Fireship") — treat as YouTube handle
    if url_or_id.startswith("@"):
        url_or_id = f"https://www.youtube.com/{url_or_id}"

    # /@handle or /c/name — extract the handle, then verify via API
    handle_match = re.search(r"youtube\.com/(@[\w.-]+|c/[\w.-]+)", url_or_id)
    if handle_match:
        handle = handle_match.group(1)
        expected_name = handle.lstrip("@").replace("c/", "")

        # Method 1: Use YouTube API forHandle (most reliable)
        if api_key:
            try:
                resp = httpx.get(f"{YOUTUBE_API_URL}/channels", params={
                    "key": api_key, "forHandle": expected_name, "part": "snippet"
                }, timeout=15)
                items = resp.json().get("items", [])
                if items:
                    cid = items[0]["id"]
                    name = items[0]["snippet"]["title"]
                    return cid, name
            except Exception:
                pass

            # Method 2: forHandle didn't work (handle may have been redirected)
            # Search for the channel by name
            found = _search_channel(expected_name, api_key)
            if found:
                return found

        # Method 3: Fallback to page scraping
        resp = httpx.get(url_or_id, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        m = re.search(r'"channelId":"(UC[\w-]+)"', resp.text)
        if m:
            name_match = re.search(r'<meta property="og:title" content="([^"]+)"', resp.text)
            scraped_name = name_match.group(1) if name_match else expected_name
            return m.group(1), scraped_name

    # Method 4: Treat input as a channel name and search for it
    if api_key:
        found = _search_channel(url_or_id, api_key)
        if found:
            return found

    raise ValueError(f"Cannot resolve channel from: {url_or_id}")


def _names_match(expected, actual):
    """Check if channel names roughly match (case-insensitive, ignore spaces)."""
    e = re.sub(r'[\s_-]', '', expected).lower()
    a = re.sub(r'[\s_-]', '', actual).lower()
    return e in a or a in e


def _get_channel_name(channel_id, api_key=None):
    """Look up a channel's name via the YouTube API."""
    if not api_key:
        return None
    try:
        resp = httpx.get(f"{YOUTUBE_API_URL}/channels", params={
            "key": api_key, "id": channel_id, "part": "snippet"
        }, timeout=15)
        items = resp.json().get("items", [])
        if items:
            return items[0]["snippet"]["title"]
    except Exception:
        pass
    return None


def _search_channel(name, api_key):
    """Search YouTube for a channel by name, return (channel_id, channel_name) or None."""
    try:
        resp = httpx.get(f"{YOUTUBE_API_URL}/search", params={
            "key": api_key, "q": name, "type": "channel",
            "part": "snippet", "maxResults": 5,
        }, timeout=15)
        for item in resp.json().get("items", []):
            title = item["snippet"]["title"]
            cid = item["id"]["channelId"]
            if _names_match(name, title):
                print(f"  Found: {title} ({cid})")
                return cid, title
    except Exception:
        pass
    return None

# --- YouTube API ---

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"

def fetch_latest_videos(channel_id, api_key=None, max_results=2, channel_name=""):
    if api_key:
        # Use playlistItems API with the channel's uploads playlist (UC -> UU)
        # This returns ONLY videos from this specific channel
        uploads_playlist = "UU" + channel_id[2:]
        params = {
            "key": api_key, "playlistId": uploads_playlist, "part": "snippet",
            "maxResults": max_results,
        }
        resp = httpx.get(f"{YOUTUBE_API_URL}/playlistItems", params=params, timeout=30)
        resp.raise_for_status()
        videos = []
        for item in resp.json().get("items", []):
            snippet = item.get("snippet", {})
            vid_id = snippet.get("resourceId", {}).get("videoId", "")
            if vid_id:
                videos.append({
                    "video_id": vid_id, "title": snippet.get("title", "Untitled"),
                    "published_at": snippet.get("publishedAt", ""),
                    "channel_name": snippet.get("channelTitle", channel_name or channel_id),
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

def load_system_prompt(path="prompt.txt"):
    """Load system prompt from prompt.txt. Lines starting with ## are stripped. Falls back to a basic default if file is missing."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            lines = [line for line in f if not line.startswith("##")]
            return "\n".join(lines).strip()
    return "You are a video summarizer. Given a transcript, produce a JSON object with \"summary\" (string) and \"sections\" (array of {timestamp, title, description}). Output ONLY valid JSON."

SYSTEM_PROMPT = load_system_prompt()

def parse_json_response(text):
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text)

def _validate_result(result):
    """Check that the result has both summary and non-empty sections."""
    if not isinstance(result, dict):
        return False
    if not result.get("summary"):
        return False
    if not result.get("sections") or len(result["sections"]) == 0:
        return False
    return True

def summarize_with_claude(transcript, video_title, api_key, model="claude-opus-4-6"):
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    max_chars = 400000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[transcript truncated]"
    for attempt in range(3):
        messages = [{"role": "user", "content": f"Video title: {video_title}\n\nTranscript:\n{transcript}"}]
        # On retry, add explicit reminder about sections
        if attempt > 0:
            messages[0]["content"] += "\n\nIMPORTANT: You MUST include a non-empty \"sections\" array with timestamped chapters. Do not put everything in the summary."
        resp = client.messages.create(
            model=model, max_tokens=4096, system=SYSTEM_PROMPT,
            messages=messages,
        )
        try:
            result = parse_json_response(resp.content[0].text)
            if _validate_result(result):
                return result
            # Valid JSON but missing sections — retry
            if attempt == 2:
                return result  # Return what we have on last attempt
        except json.JSONDecodeError:
            if attempt == 2:
                raise ValueError(f"Failed to parse JSON after 3 attempts. Raw response: {resp.content[0].text[:300]}")

def summarize_with_groq(transcript, video_title, api_key, model="llama-3.3-70b-versatile"):
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    max_chars = 28000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[transcript truncated]"
    for attempt in range(3):
        user_content = f"Video title: {video_title}\n\nTranscript:\n{transcript}"
        if attempt > 0:
            user_content += "\n\nIMPORTANT: You MUST include a non-empty \"sections\" array with timestamped chapters."
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
        result = parse_json_response(resp.choices[0].message.content)
        if _validate_result(result):
            return result
        if attempt == 2:
            return result
    return result

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
    """Convert M:SS, MM:SS, or H:MM:SS to total seconds."""
    try:
        parts = ts.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return 0

def _seconds_to_display(seconds):
    """Convert total seconds to a human-readable duration like '~18 min'."""
    if seconds < 60:
        return f"~{seconds} sec"
    minutes = round(seconds / 60)
    return f"~{minutes} min"

def generate_channel_pdf(channel_name, video_summaries, output_dir="./pdfs"):
    """Generate a visually enhanced PDF with all video summaries for a channel."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, HRFlowable
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT

    day_dir = os.path.join(output_dir, datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(day_dir, exist_ok=True)
    safe_name = re.sub(r'[^\w\s-]', '', channel_name)[:40].strip()
    filename = f"{safe_name}.pdf"
    filepath = os.path.join(day_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()

    def esc(text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # --- Style definitions ---
    channel_title_style = ParagraphStyle('CT', parent=styles['Heading1'], fontSize=24, spaceAfter=2)
    channel_sub_style = ParagraphStyle('CSub', parent=styles['Normal'], fontSize=11,
                                       textColor=HexColor('#555555'), spaceAfter=4)
    video_title_style = ParagraphStyle('VT', parent=styles['Heading1'], fontSize=16, spaceAfter=4)
    meta_style = ParagraphStyle('M', parent=styles['Normal'], fontSize=10, textColor=HexColor('#666666'))
    stats_style = ParagraphStyle('Stats', parent=styles['Normal'], fontSize=10,
                                 textColor=HexColor('#888888'), fontName='Helvetica-Oblique', spaceAfter=6)
    summary_style = ParagraphStyle('SumBody', parent=styles['BodyText'], fontSize=11,
                                   leading=15, leftIndent=6, rightIndent=6,
                                   spaceBefore=4, spaceAfter=4)
    nav_header_style = ParagraphStyle('NavH', parent=styles['Normal'], fontSize=10,
                                      fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=2)
    nav_style = ParagraphStyle('Nav', parent=styles['Normal'], fontSize=9,
                               leading=13, leftIndent=12, textColor=HexColor('#333333'))
    section_style = ParagraphStyle('S', parent=styles['Heading3'], fontSize=12, spaceBefore=10)
    footer_style = ParagraphStyle('F', parent=styles['Normal'], fontSize=8, textColor=HexColor('#999999'))

    # Colors
    accent_color = HexColor('#2a7ae2')
    border_color = HexColor('#cccccc')
    light_bg = HexColor('#f0f0f0')
    link_color = HexColor('#0066cc')

    elements = []

    # --- Channel header ---
    elements.append(Paragraph(esc(channel_name), channel_title_style))
    num_videos = len(video_summaries)
    elements.append(Paragraph(
        f"{num_videos} video{'s' if num_videos != 1 else ''} summarized \u2014 {datetime.now().strftime('%B %d, %Y')}",
        channel_sub_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=accent_color, spaceAfter=16))

    for i, vs in enumerate(video_summaries):
        if i > 0:
            elements.append(Spacer(1, 12))
            elements.append(HRFlowable(width="100%", thickness=1, color=border_color,
                                       spaceBefore=8, spaceAfter=16))

        title = vs["title"]
        url = vs["url"]
        result = vs["result"]
        sections = result.get("sections", [])

        # --- Video title and URL ---
        elements.append(Paragraph(esc(title), video_title_style))
        safe_url = url.replace("&", "&amp;")
        elements.append(Paragraph(
            f"<link href='{safe_url}'>{esc(url)}</link>", meta_style))

        # --- Quick stats line ---
        num_sections = len(sections)
        if sections:
            last_ts = sections[-1].get("timestamp", "0:00")
            total_secs = _timestamp_to_seconds(last_ts)
            duration_str = _seconds_to_display(total_secs) if total_secs > 0 else ""
        else:
            duration_str = ""
        stats_parts = [f"{num_sections} section{'s' if num_sections != 1 else ''}"]
        if duration_str:
            stats_parts.append(duration_str)
        elements.append(Paragraph(" | ".join(stats_parts), stats_style))
        elements.append(Spacer(1, 4))

        # --- Summary highlight box ---
        summary_text = result.get("summary", "")
        if summary_text:
            elements.append(Paragraph("<b>Summary</b>", styles['Heading2']))
            summary_para = Paragraph(esc(summary_text), summary_style)
            # Colored left-border box: narrow accent cell + content cell
            page_width = letter[0] - 2 * 0.75 * inch
            summary_table = Table(
                [[None, summary_para]],
                colWidths=[4, page_width - 4]
            )
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), accent_color),
                ('BACKGROUND', (1, 0), (1, 0), light_bg),
                ('LEFTPADDING', (1, 0), (1, 0), 10),
                ('RIGHTPADDING', (1, 0), (1, 0), 10),
                ('TOPPADDING', (1, 0), (1, 0), 8),
                ('BOTTOMPADDING', (1, 0), (1, 0), 8),
                ('LEFTPADDING', (0, 0), (0, 0), 0),
                ('RIGHTPADDING', (0, 0), (0, 0), 0),
                ('TOPPADDING', (0, 0), (0, 0), 0),
                ('BOTTOMPADDING', (0, 0), (0, 0), 0),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 8))

        # --- Divider between summary and timestamps ---
        if sections:
            elements.append(HRFlowable(width="100%", thickness=0.5, color=border_color,
                                       spaceBefore=4, spaceAfter=8))

            # --- Table of Contents (Quick Navigation) ---
            elements.append(Paragraph("Quick Navigation:", nav_header_style))
            for sec in sections:
                ts = sec.get("timestamp", "")
                stitle = sec.get("title", "")
                ts_seconds = _timestamp_to_seconds(ts)
                if ts_seconds > 0:
                    ts_url = f"https://youtube.com/watch?v={vs['url'].split('v=')[-1]}&amp;t={ts_seconds}"
                else:
                    ts_url = safe_url
                nav_line = (
                    f"<link href='{ts_url}'>"
                    f"<font color='#0066cc'><u>{esc(ts)}</u></font></link>"
                    f"&nbsp;&nbsp;{esc(stitle)}"
                )
                elements.append(Paragraph(nav_line, nav_style))
            elements.append(Spacer(1, 10))

            # --- Detailed Sections ---
            elements.append(Paragraph("<b>Timestamps</b>", styles['Heading2']))
            for sec in sections:
                ts = sec.get("timestamp", "")
                stitle = sec.get("title", "")
                desc = sec.get("description", "")
                ts_seconds = _timestamp_to_seconds(ts)
                if ts_seconds > 0:
                    ts_url = f"https://youtube.com/watch?v={vs['url'].split('v=')[-1]}&amp;t={ts_seconds}"
                else:
                    ts_url = safe_url
                # Timestamp: blue underlined link; title: bold black
                section_heading = (
                    f"<link href='{ts_url}'>"
                    f"<font color='#0066cc'><u>{esc(ts)}</u></font></link>"
                    f" <b>\u2014 {esc(stitle)}</b>"
                )
                elements.append(Paragraph(section_heading, section_style))
                elements.append(Paragraph(esc(desc), styles['BodyText']))

    # --- Footer ---
    elements.append(Spacer(1, 24))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceAfter=6))
    elements.append(Paragraph(
        f"Generated by YT Summarizer on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        footer_style))

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
    videos_to_check = int(config.get("VIDEOS_TO_CHECK", "2"))
    pdf_dir = config.get("PDF_DIR", "./pdfs").strip()

    all_results = {}  # channel_name -> list of {title, url, result}
    all_pdfs = []
    total_new = 0
    total_processed = 0

    for channel_input in channels:
        print(f"\n{'─' * 50}")
        try:
            channel_id, channel_name = resolve_channel_id(channel_input, youtube_api_key)
            print(f"Channel: {channel_name} ({channel_id})")
        except Exception as e:
            print(f"SKIP: Cannot resolve '{channel_input}': {e}")
            continue

        try:
            videos = fetch_latest_videos(channel_id, youtube_api_key, max_results=videos_to_check, channel_name=channel_name)
            # Warn if videos come from a different channel than expected
            if videos and videos[0].get("channel_name") and videos[0]["channel_name"] != channel_name:
                actual = videos[0]["channel_name"]
                print(f"  WARNING: @handle resolved to '{actual}' instead of '{channel_name}'")
                print(f"  TIP: Use the channel ID directly in channels.txt: {channel_id}")
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
