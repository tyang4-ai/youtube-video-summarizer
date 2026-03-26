# YouTube Video Summarizer

A web application that monitors YouTube channels, auto-generates timestamped summaries via LLM (Grok/Claude), creates PDFs, and emails them to a configurable mailing list.

## Features

- **Monitor YouTube channels** for new videos via RSS feeds
- **Auto-generate timestamped summaries** using Grok (xAI) or Claude (Anthropic) APIs
- **Create well-formatted PDF** summaries with ReportLab
- **Email summaries** to a configurable mailing list (encrypted SMTP credentials)
- **Dashboard** with stats and recent activity feed
- **Configurable polling intervals** per channel via APScheduler

## Tech Stack

| Layer      | Technology                                      |
|------------|--------------------------------------------------|
| Backend    | Python 3.11, FastAPI, SQLAlchemy, APScheduler, SQLite |
| Frontend   | React 18, TypeScript, Vite                       |
| LLM        | Grok (xAI) / Claude (Anthropic)                 |
| PDF        | ReportLab                                        |
| Deployment | Railway (Nixpacks)                               |

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Grok (xAI) or Anthropic API key

## Local Development Setup

```bash
# Clone the repo
git clone <repo-url>
cd youtube-video-summarizer

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Configure environment
cd ..
cp .env.example .env
# Edit .env with your API keys and SMTP settings

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add the output as ENCRYPTION_KEY in .env

# Run backend
cd backend
uvicorn app.main:app --reload

# Run frontend (separate terminal)
cd frontend
npm run dev
```

## Environment Variables

| Variable          | Description                                            | Default                            |
|-------------------|--------------------------------------------------------|------------------------------------|
| `LLM_PROVIDER`    | LLM backend to use (`grok` or `claude`)                | `grok`                             |
| `XAI_API_KEY`     | API key for Grok (xAI) - required if provider is grok  |                                    |
| `ANTHROPIC_API_KEY` | API key for Claude (Anthropic) - required if provider is claude |                           |
| `DATABASE_URL`    | SQLAlchemy database URL                                | `sqlite:///./data/yt_summarizer.db`|
| `PDF_DIR`         | Directory to store generated PDFs                      | `./data/pdfs`                      |
| `ENCRYPTION_KEY`  | Fernet key for encrypting SMTP credentials             |                                    |
| `HOST`            | Server bind host                                       | `0.0.0.0`                          |
| `PORT`            | Server bind port                                       | `8000`                             |

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Railway Deployment

1. Push to GitHub
2. Connect the repo in the Railway dashboard
3. Set environment variables in Railway (see table above)
4. Railway auto-deploys from the main branch using Nixpacks

The build process (`build.sh`) compiles the React frontend and copies the static assets into the backend for serving.

## Project Structure

```
youtube-video-summarizer/
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI route handlers
│   │   │   ├── channels.py    #   Channel CRUD endpoints
│   │   │   ├── dashboard.py   #   Dashboard stats endpoint
│   │   │   ├── email.py       #   Email settings endpoints
│   │   │   └── summaries.py   #   Summary endpoints + PDF download
│   │   ├── services/           # Business logic
│   │   │   ├── llm/           #   LLM provider abstraction
│   │   │   │   ├── base.py    #     Abstract base provider
│   │   │   │   ├── grok_provider.py
│   │   │   │   ├── claude_provider.py
│   │   │   │   └── factory.py #     Provider factory
│   │   │   ├── channel_resolver.py  # YouTube URL/handle resolver
│   │   │   ├── emailer.py     #   SMTP email service
│   │   │   ├── job_logger.py  #   Job execution logger
│   │   │   ├── pdf_generator.py #  PDF creation with ReportLab
│   │   │   ├── pipeline.py    #   End-to-end processing pipeline
│   │   │   ├── poller.py      #   RSS feed poller
│   │   │   ├── scheduler.py   #   APScheduler management
│   │   │   ├── summarizer.py  #   LLM summarization orchestrator
│   │   │   └── transcriber.py #   YouTube transcript fetcher
│   │   ├── config.py          # Pydantic settings
│   │   ├── database.py        # SQLAlchemy engine & session
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   └── schemas.py         # Pydantic request/response schemas
│   ├── tests/                  # Pytest test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/               # API client modules
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Page-level components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Channels.tsx
│   │   │   ├── Summaries.tsx
│   │   │   └── EmailSettings.tsx
│   │   ├── App.tsx            # Root component with routing
│   │   └── types.ts           # TypeScript type definitions
│   ├── package.json
│   └── vite.config.ts
├── .env.example               # Environment variable template
├── build.sh                   # Frontend build + copy script
├── Procfile                   # Railway process definition
├── railway.toml               # Railway build/deploy config
├── runtime.txt                # Python version specification
└── README.md
```
