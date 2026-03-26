# YouTube Video Summarizer — Design Spec

## Overview

A single-user webapp that monitors YouTube channels for new videos, automatically generates timestamped summaries using a cloud LLM API (Grok initially, designed to swap to Claude Opus), produces well-formatted PDFs, and emails them to a configurable mailing list. Deployed to Railway for 24/7 operation.

## Tech Stack

- **Backend:** Python, FastAPI, APScheduler, SQLAlchemy, SQLite
- **Frontend:** React (TypeScript), Vite
- **Summarization:** Grok API (xAI) — proof of concept; swappable to Claude Opus (Anthropic)
- **Deployment:** Railway
- **Transcripts:** youtube-transcript-api
- **PDF Generation:** ReportLab
- **Email:** SMTP (stdlib smtplib)
- **Channel Polling:** YouTube RSS feeds via feedparser

## Configuration

Application settings are loaded from a `.env` file in the project root:

- `LLM_PROVIDER` — Which LLM API to use: `grok` or `claude` (default: `grok`)
- `XAI_API_KEY` — xAI API key for Grok
- `ANTHROPIC_API_KEY` — Anthropic API key for Claude (used when switching to Claude Opus)
- `DATABASE_URL` — SQLite path (default: `sqlite:///./data/yt_summarizer.db`)
- `PDF_DIR` — Directory for generated PDFs (default: `./data/pdfs/`)
- `ENCRYPTION_KEY` — Fernet key for encrypting SMTP password at rest (generate via `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `HOST` / `PORT` — FastAPI bind address (default: `0.0.0.0:8000`)

These are loaded via Pydantic Settings (`pydantic-settings` package).

## Architecture

Single FastAPI process (monolith) with APScheduler running in-process. SQLite runs in WAL mode for better concurrency with simultaneous API requests and scheduler jobs. CORS is configured to allow the React dev server during development.

### Pipeline Flow

```
Poll RSS → New video? → Get Transcript → Summarize (Grok/Claude API) → Generate PDF → Send Email
```

### Components

1. **REST API** — serves React frontend (static build) and handles CRUD for channels, summaries, and email config
2. **APScheduler** — runs per-channel polling jobs on configurable intervals
3. **Service Layer** — poller, transcriber, summarizer, PDF generator, emailer
4. **SQLite DB** — stores all persistent state

### New Video Detection

Uses free YouTube RSS feeds (`https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID`). Compares video IDs from the feed against stored `video_id` values in the database to detect new uploads. No API key required.

### Channel URL Resolution

When a user adds a channel, the app accepts multiple URL formats and resolves them to a `channel_id`:

- `https://www.youtube.com/channel/UCxxxx` — extract ID directly
- `https://www.youtube.com/@handle` — fetch the page and extract the channel ID from the page metadata
- `https://www.youtube.com/c/customname` — same as @handle, fetch and extract
- Raw channel ID (`UCxxxx`) — use directly

### Startup & Shutdown

- **Startup:** On boot, read all active channels from the DB and register their polling jobs with APScheduler. Do not immediately poll — let jobs fire on their configured intervals. Videos left in `pending` status from a prior crash are re-queued for processing.
- **Shutdown:** APScheduler's graceful shutdown waits for running jobs to finish before exiting.

## Database Schema

### channels
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| youtube_channel_id | TEXT UNIQUE | YouTube channel ID |
| last_polled_at | DATETIME | Nullable, last successful poll time |
| name | TEXT | Channel display name |
| url | TEXT | Channel URL |
| poll_interval_minutes | INTEGER | Default 60 |
| is_active | BOOLEAN | Default true |
| created_at | DATETIME | Auto-set |

### videos
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| channel_fk | INTEGER FK | References channels.id |
| youtube_video_id | TEXT UNIQUE | YouTube video ID |
| transcript_text | TEXT | Nullable, cached raw transcript |
| title | TEXT | Video title |
| published_at | DATETIME | From RSS feed |
| status | TEXT | pending / summarized / failed |
| error_message | TEXT | Nullable, reason for failure |
| created_at | DATETIME | Auto-set |

### summaries
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| video_id | INTEGER FK | References videos.id |
| summary_text | TEXT | Overview paragraph |
| timestamps_json | TEXT | JSON array of {timestamp, title, description} |
| pdf_path | TEXT | Path to generated PDF file |
| email_sent | BOOLEAN | Default false |
| created_at | DATETIME | Auto-set |

### email_config
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Single row |
| smtp_host | TEXT | e.g. smtp.gmail.com |
| smtp_port | INTEGER | e.g. 587 |
| smtp_user | TEXT | Login username |
| smtp_password | TEXT | Encrypted at rest (Fernet symmetric encryption, key from .env) |
| sender_email | TEXT | From address |
| recipients_json | TEXT | JSON array of email addresses |
| is_active | BOOLEAN | Toggle email sending |

### job_log
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| channel_fk | INTEGER FK | Nullable |
| video_fk | INTEGER FK | Nullable |
| action | TEXT | poll / transcribe / summarize / pdf / email |
| status | TEXT | success / failed |
| error_message | TEXT | Nullable |
| created_at | DATETIME | Auto-set |

## API Endpoints

### Channels
- `GET /api/channels` — list all channels
- `POST /api/channels` — add a channel (accepts URL or channel ID)
- `PUT /api/channels/{id}` — update channel (poll interval, active status)
- `DELETE /api/channels/{id}` — remove channel and cancel its polling job
- `POST /api/channels/{id}/poll` — force immediate poll

### Summaries
- `GET /api/summaries?channel_id={id}` — list all summaries (optional channel filter)
- `GET /api/summaries/{id}` — get full summary with timestamps
- `GET /api/summaries/{id}/pdf` — download PDF file
- `POST /api/summaries/{id}/resend` — re-send email for this summary
- `POST /api/summaries/{id}/regenerate` — re-generate summary from transcript

### Email Config
- `GET /api/email` — get current email config (password masked)
- `PUT /api/email` — update email config
- `POST /api/email/test` — send a test email

### Dashboard
- `GET /api/dashboard` — stats (channel count, videos processed, emails sent, next poll time)
- `GET /api/activity` — recent activity feed from job_log

## UI Pages

### Dashboard
- Stats cards: channels count, videos processed, emails sent, next poll countdown
- Recent activity feed with status badges (SENT, PROCESSING, FAILED)

### Channels
- Table of monitored channels with name, URL, poll interval, status, last checked
- "Add Channel" form (URL input + poll interval selector)
- Per-row actions: edit interval, toggle active/pause, check now, delete

### Summaries
- List of generated summaries with video title, channel, date, status
- Filter by channel dropdown
- Click to expand: full summary text + timestamped sections
- Action buttons: download PDF, re-send email, re-generate

### Email Settings
- SMTP configuration form (host, port, user, password, sender)
- Recipient list with add/remove
- Test email button
- Master toggle for email sending

## PDF Layout

1. **Header** — channel name, video title, publish date, video URL
2. **Summary** — concise overview paragraph (2-3 sentences)
3. **Timestamped Sections** — each section: timestamp link, section title, 2-3 sentence description
4. **Footer** — generation date, "Generated by YT Summarizer"

## LLM Summarization

The summarizer sends the transcript to the configured LLM API (Grok or Claude) requesting structured JSON output.

### LLM Provider Abstraction

The summarizer uses a provider interface so swapping between Grok and Claude is a config change:

- **Grok (xAI):** Uses the OpenAI-compatible API at `https://api.x.ai/v1`. Model: `grok-3`. Context window: 131K tokens.
- **Claude (Anthropic):** Uses the Anthropic SDK. Model: `claude-opus-4-6`. Context window: 200K tokens.

Both providers are called via a common `LLMProvider` interface with a `summarize(transcript: str) -> dict` method. The `LLM_PROVIDER` env var selects which one is active.

### Context Window Handling

Transcripts are split into chunks that fit the model's context window. For long videos (Grok: 131K tokens, Claude: 200K tokens — most videos will fit in a single pass):

1. Split transcript into overlapping chunks by timestamp boundaries
2. Summarize each chunk individually, requesting timestamped sections
3. Merge chunk summaries into a single cohesive summary with a final pass

For short videos (under context limit), process in a single pass.

### Output Format

```json
{
  "summary": "2-3 sentence overview of the video",
  "sections": [
    {
      "timestamp": "0:00",
      "title": "Introduction",
      "description": "2-3 sentence summary of this segment"
    }
  ]
}
```

The prompt instructs the model to identify natural topic boundaries in the transcript and create meaningful timestamp sections. The transcript already includes timing data from youtube-transcript-api.

### JSON Parsing Robustness

If the LLM returns malformed JSON, the summarizer retries up to 2 times. If all retries fail, mark the video as `failed` with the error logged.

### Email Content

- **Subject:** `[YT Summary] {video_title} — {channel_name}`
- **Body:** Plain text with the summary overview and a link to the video
- **Attachment:** The formatted PDF with full timestamped summary

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No captions available | Mark video as `failed`, log reason, skip. Show in dashboard. |
| LLM API error (rate limit, timeout, auth) | Retry once after 30s, then mark failed. Show warning in UI. |
| SMTP failure | Retry once, mark email unsent. PDF still saved for manual re-send. |
| Invalid channel URL | Validate on input, reject with error message. |
| Duplicate video | Skip if `video_id` already exists in database. |
| RSS feed unavailable | Log error, retry on next poll cycle. |

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app, startup, static file serving
    api/
      channels.py        # Channel CRUD endpoints
      summaries.py       # Summary endpoints
      email.py           # Email config endpoints
      dashboard.py       # Dashboard/activity endpoints
    services/
      poller.py          # YouTube RSS polling logic
      transcriber.py     # Transcript fetching via youtube-transcript-api
      summarizer.py      # LLM summarization (Grok/Claude provider interface)
      pdf_generator.py   # ReportLab PDF creation
      emailer.py         # SMTP email sending
      scheduler.py       # APScheduler setup and job management
    models.py            # SQLAlchemy ORM models
    database.py          # SQLite engine and session
    schemas.py           # Pydantic request/response schemas
  requirements.txt

frontend/
  src/
    components/          # Sidebar, StatsCard, StatusBadge, etc.
    pages/               # Dashboard, Channels, Summaries, EmailSettings
    api/                 # Axios API client functions
    App.tsx
    main.tsx
  package.json
  vite.config.ts
```

## Deployment (Railway)

The app is deployed to Railway as a single service:

- **Backend:** Python FastAPI process (serves both API and React static build)
- **Database:** SQLite file stored on a Railway persistent volume
- **PDFs:** Stored on the same persistent volume under `./data/pdfs/`
- **Environment variables:** All secrets (`XAI_API_KEY`, `ENCRYPTION_KEY`, SMTP creds) configured via Railway dashboard
- **Build:** Railway auto-detects Python via `requirements.txt`. A build script runs `npm run build` in the frontend directory and copies the output to the backend's static directory.
- **Procfile:** `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Deployment Files

```
Procfile                 # Railway process definition
railway.toml             # Railway config (build command, volumes)
```

## Verification Plan

1. **Backend unit tests:** test each service in isolation (poller, transcriber, summarizer, PDF generator, emailer)
2. **API integration tests:** test each endpoint with a test SQLite database
3. **Manual end-to-end test (local):**
   - Set `XAI_API_KEY` in `.env`
   - Run FastAPI + React dev server locally
   - Add a YouTube channel via the UI
   - Force poll → verify transcript fetch → verify summary generation → verify PDF creation → verify email delivery
4. **Railway deployment test:**
   - Push to GitHub → Railway auto-deploys
   - Verify the app is accessible at the Railway URL
   - Add a channel, trigger a poll, confirm email arrives
5. **Edge cases:** test with channels that have no captions, very long videos, channels with no recent uploads
6. **Provider swap test:** Switch `LLM_PROVIDER` from `grok` to `claude`, verify summarization still works
