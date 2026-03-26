# YouTube Video Summarizer (CLI)

A command-line tool that monitors your favorite YouTube channels, automatically summarizes new videos using AI, generates clean PDF reports, and emails you a daily digest. Run it once a day and never miss what matters.

## Features

- **One PDF per channel** -- each channel gets its own PDF with page breaks between videos
- **Single daily email** -- one digest email with all summaries and PDFs attached
- **Tracks seen videos** -- only processes new videos (won't re-summarize ones you've already seen)
- **Two AI providers** -- supports Claude (Anthropic) and Groq (free, uses Llama 3.3 70B)
- **Timestamped sections** -- summaries include chapter breakdowns with timestamps you can jump to
- **Handles multiple channels** -- add as many channels as you want to `channels.txt`
- **Zero dependencies to start** -- the run script auto-creates a virtual environment and installs everything

## Quick Start

1. **Clone or download** this repository
2. **Copy the example config:**
   ```
   cp config.example.txt config.txt
   ```
3. **Edit `config.txt`** -- fill in your API keys (see [Getting Credentials](#getting-credentials) below)
4. **Edit `channels.txt`** -- add the YouTube channels you want to follow
5. **Run it:**
   - **Windows:** double-click `run.bat`
   - **Mac/Linux:** run `./run.sh`

That's it. On the first run, it will create a virtual environment and install dependencies automatically.

## Getting Credentials

You need a few API keys to make everything work. Here's exactly how to get each one.

### Anthropic API Key (for Claude)

Use this if you want Claude as your summarization engine.

1. Go to [https://console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Click **API Keys** in the left sidebar
4. Click **Create Key**
5. Copy the key (it starts with `sk-ant-`)
6. Paste it into `config.txt`:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   LLM_PROVIDER=claude
   ```

Note: Claude is a paid API. Check [Anthropic's pricing page](https://www.anthropic.com/pricing) for current rates.

### Groq API Key (free alternative)

Groq offers a free tier that works well for summarization using Llama 3.3 70B.

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up or log in (free account)
3. Click **API Keys** in the left sidebar
4. Click **Create API Key**
5. Copy the key (it starts with `gsk_`)
6. Paste it into `config.txt`:
   ```
   GROQ_API_KEY=gsk_your-key-here
   LLM_PROVIDER=groq
   ```

Note: The free tier has rate limits, but it's more than enough for a daily summarizer.

### YouTube Data API Key (for finding new videos)

This is used to check channels for their latest uploads.

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Open the **API Library** (search for it in the top search bar)
4. Search for **YouTube Data API v3** and click **Enable**
5. Go to **Credentials** in the left sidebar
6. Click **Create Credentials** > **API Key**
7. Copy the key
8. Paste it into `config.txt`:
   ```
   YOUTUBE_API_KEY=AIza-your-key-here
   ```

**Free quota:** 10,000 units per day. Each channel check uses roughly 100 units, so you can monitor ~100 channels daily without paying anything.

**Optional:** If you don't set a YouTube API key, the tool falls back to RSS feeds, but this is less reliable.

### Resend API Key (for email)

Resend handles sending the daily digest email with PDF attachments.

1. Go to [https://resend.com](https://resend.com)
2. Sign up (free tier gives you 100 emails/day)
3. Go to **API Keys** in the dashboard
4. Click **Create API Key**
5. Copy the key (it starts with `re_`)
6. Paste it into `config.txt`:
   ```
   RESEND_API_KEY=re_your-key-here
   ```

**Important notes about the free tier:**
- The free tier can only send emails **to the email address you signed up with**. Set that address as your `RECIPIENTS` in config.txt.
- To send to other people, you need to verify your own domain at [resend.com/domains](https://resend.com/domains).
- The default sender `onboarding@resend.dev` works immediately with no setup.

**Optional:** If you don't set a Resend key, the tool still runs -- it just skips the email step and only generates PDFs.

## Configuration

All settings live in `config.txt`. Here is every field explained:

```
# Which AI to use: "claude" or "groq"
LLM_PROVIDER=claude

# API key for Claude (required if LLM_PROVIDER=claude)
ANTHROPIC_API_KEY=

# API key for Groq (required if LLM_PROVIDER=groq)
GROQ_API_KEY=

# Override the default model (leave blank to use the default)
# Groq default: llama-3.3-70b-versatile
# Claude default: claude-opus-4-6
MODEL=

# Resend API key for sending email (optional)
RESEND_API_KEY=

# The "from" address on the email
SENDER_EMAIL=onboarding@resend.dev

# Comma-separated list of email recipients
RECIPIENTS=email1@example.com

# YouTube Data API key (optional, falls back to RSS without it)
YOUTUBE_API_KEY=

# Where to save generated PDFs
PDF_DIR=./pdfs
```

Lines starting with `#` are comments and are ignored.

## Adding Channels

Edit `channels.txt` and add one channel per line. Blank lines and lines starting with `#` are ignored.

```
# Tech channels
https://www.youtube.com/@fireship
https://www.youtube.com/@TheDiaryOfACEO

# Science
https://www.youtube.com/@veritasium

# You can also use direct channel URLs
https://www.youtube.com/channel/UCsBjURrPoezykLs9EqgamOA
```

**Supported formats:**

| Format | Example |
|--------|---------|
| Handle URL | `https://www.youtube.com/@fireship` |
| Custom URL | `https://www.youtube.com/c/Fireship` |
| Channel URL | `https://www.youtube.com/channel/UCsBjURrPoezykLs9EqgamOA` |
| Raw channel ID | `UCsBjURrPoezykLs9EqgamOA` |

## How It Works

The tool runs a simple pipeline each time you execute it:

```
1. Poll channels     Check each channel for its latest 2 videos
        |
2. Filter new        Skip any videos already in seen_videos.json
        |
3. Get transcript    Fetch the English transcript from YouTube
        |
4. Summarize         Send transcript to Claude or Groq for AI summarization
        |
5. Generate PDF      Create one PDF per channel with all new video summaries
        |
6. Send email        Send a single digest email with all PDFs attached
        |
7. Save state        Update seen_videos.json so videos aren't processed again
```

Each summary includes:
- A 3-5 sentence overview of the video's core points
- 5-15 timestamped sections with detailed descriptions

## Output

### PDFs

PDFs are saved to the `./pdfs/` directory (configurable via `PDF_DIR` in config.txt).

Each PDF is named with the channel name and date:
```
pdfs/
  TheDiaryOfACEO_20260326.pdf
  fireship_20260326.pdf
```

Inside each PDF:
- Channel name and date header
- One page per video, with page breaks between them
- Video title and YouTube link
- Full summary paragraph
- Timestamped section breakdown

### Email

If configured, you get one email per run with:
- Subject line: `[YT Summary] Daily Digest -- Mar 26, 2026`
- Plain-text body with a quick summary of each video
- All PDFs attached

### Seen Videos

The file `seen_videos.json` tracks every video ID that has been processed. This is how the tool knows to skip videos on the next run. You can delete this file to reprocess everything.

## Daily Usage

The simplest way to use this tool is to run it once a day:

- **Windows:** Double-click `run.bat`. It opens a terminal, runs the summarizer, and pauses so you can read the output.
- **Mac/Linux:** Open a terminal and run `./run.sh` (you may need to `chmod +x run.sh` the first time).

The first run creates a `.venv/` virtual environment and installs all dependencies from `requirements.txt`. Subsequent runs reuse the existing environment.

## Scheduling (Optional)

You can automate this so it runs every morning without you thinking about it.

### Windows -- Task Scheduler

1. Open **Task Scheduler** (search for it in the Start menu)
2. Click **Create Basic Task**
3. Name it something like "YouTube Summarizer"
4. Set the trigger to **Daily** and pick a time (e.g., 7:00 AM)
5. For the action, choose **Start a Program**
6. Set the program to the full path of `run.bat`:
   ```
   C:\path\to\cli\run.bat
   ```
7. Set "Start in" to the cli directory:
   ```
   C:\path\to\cli
   ```
8. Finish the wizard

### Mac/Linux -- cron

1. Open your crontab:
   ```bash
   crontab -e
   ```
2. Add a line to run daily at 7:00 AM:
   ```
   0 7 * * * /path/to/cli/run.sh >> /path/to/cli/cron.log 2>&1
   ```
3. Save and exit

The `>> cron.log 2>&1` part saves the output to a log file so you can check it if something goes wrong.

## Troubleshooting

### "No channels in channels.txt"
You haven't added any channels yet. Open `channels.txt` and add at least one YouTube channel URL.

### "ANTHROPIC_API_KEY not set" or "GROQ_API_KEY not set"
Your `config.txt` is missing the API key for the provider you selected. Make sure:
- `LLM_PROVIDER` matches the key you filled in (`claude` needs `ANTHROPIC_API_KEY`, `groq` needs `GROQ_API_KEY`)
- There are no extra spaces around the `=` sign

### "Cannot resolve channel from: ..."
The channel URL format isn't recognized, or the channel page couldn't be reached. Try using the full URL from your browser's address bar, or use the raw channel ID (starts with `UC`).

### "FAILED (transcript): ..."
The video doesn't have an English transcript available. This happens with:
- Videos that have no captions at all
- Videos with only auto-generated captions in another language
- Very new videos where captions haven't been processed yet

The tool will skip that video and continue with the rest.

### "FAILED (summarize): ..."
The AI API returned an error. Common causes:
- Invalid or expired API key
- Rate limit exceeded (especially on Groq's free tier -- wait a minute and try again)
- The transcript was too long (the tool truncates, but edge cases can still fail)

### "Email failed: ..."
Check that:
- `RESEND_API_KEY` is correct
- `RECIPIENTS` contains valid email addresses
- If on the free tier, you can only send to the email you signed up with

### PDFs are not being generated
Make sure `reportlab` is installed. If you're running manually (not via run.bat/run.sh), install dependencies with:
```bash
pip install -r requirements.txt
```

### I want to re-summarize old videos
Delete `seen_videos.json` (or remove specific video IDs from it). The tool will treat those videos as new on the next run.

## Requirements

Python 3.8 or higher. All Python dependencies are installed automatically by the run scripts:

- `anthropic` -- Claude API client
- `openai` -- used for Groq (Groq uses an OpenAI-compatible API)
- `youtube-transcript-api` -- fetches video transcripts
- `httpx` -- HTTP client for channel resolution and YouTube API calls
- `reportlab` -- PDF generation
- `resend` -- email delivery
- `feedparser` -- RSS feed fallback (used when no YouTube API key is set)
