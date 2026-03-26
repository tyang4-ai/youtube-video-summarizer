# YouTube Video Summarizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a webapp that monitors YouTube channels, auto-generates timestamped video summaries via LLM, creates PDFs, and emails them — deployed on Railway.

**Architecture:** Single FastAPI monolith with APScheduler for per-channel polling. React TypeScript frontend served as static build. SQLite with WAL mode. LLM provider abstraction (Grok first, Claude Opus later). Railway deployment with persistent volume.

**Tech Stack:** Python (FastAPI, SQLAlchemy, APScheduler, ReportLab, feedparser, youtube-transcript-api), React (TypeScript, Vite, Axios), Grok/Claude API, Railway

**Spec:** `docs/superpowers/specs/2026-03-25-youtube-summarizer-design.md`

---

## Task 1: Backend Project Scaffolding & Configuration

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_config.py`
- Create: `backend/requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Initialize git and create .gitignore**

```bash
cd "C:/Users/22317/Documents/Coding/Youtube video summarizer"
git init
```

`.gitignore`:
```
__pycache__/
*.pyc
.env
data/
*.db
node_modules/
dist/
.venv/
.superpowers/
```

- [ ] **Step 2: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
apscheduler==3.10.4
pydantic-settings==2.5.0
youtube-transcript-api==0.6.2
feedparser==6.0.11
reportlab==4.2.0
cryptography==43.0.0
openai==1.50.0
anthropic==0.34.0
httpx==0.27.0
python-multipart==0.0.9
aiofiles==24.1.0
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-cov==5.0.0
```

- [ ] **Step 3: Write the failing test for config**

`backend/tests/test_config.py`:
```python
from app.config import Settings


def test_default_settings():
    s = Settings(XAI_API_KEY="test-key", ENCRYPTION_KEY="test-enc-key")
    assert s.LLM_PROVIDER == "grok"
    assert s.DATABASE_URL == "sqlite:///./data/yt_summarizer.db"
    assert s.PDF_DIR == "./data/pdfs"
    assert s.HOST == "0.0.0.0"
    assert s.PORT == 8000


def test_llm_provider_accepts_claude():
    s = Settings(
        LLM_PROVIDER="claude",
        ANTHROPIC_API_KEY="test-key",
        ENCRYPTION_KEY="test-enc-key",
    )
    assert s.LLM_PROVIDER == "claude"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 5: Implement config.py**

`backend/app/config.py`:
```python
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    LLM_PROVIDER: Literal["grok", "claude"] = "grok"
    XAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./data/yt_summarizer.db"
    PDF_DIR: str = "./data/pdfs"
    ENCRYPTION_KEY: str = ""
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 7: Create .env.example and conftest.py**

`.env.example`:
```
LLM_PROVIDER=grok
XAI_API_KEY=
ANTHROPIC_API_KEY=
DATABASE_URL=sqlite:///./data/yt_summarizer.db
PDF_DIR=./data/pdfs
ENCRYPTION_KEY=
HOST=0.0.0.0
PORT=8000
```

`backend/tests/conftest.py`:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
```

- [ ] **Step 8: Commit**

```bash
git add .gitignore backend/ .env.example
git commit -m "feat: scaffold backend project with Pydantic Settings config"
```

---

## Task 2: Database Models

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

`backend/tests/test_models.py`:
```python
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import pytest
from app.models import Base, Channel, Video, Summary, EmailConfig, JobLog


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_create_channel(db):
    ch = Channel(youtube_channel_id="UC123", name="Test", url="https://youtube.com/@test", poll_interval_minutes=60)
    db.add(ch)
    db.commit()
    assert ch.id is not None
    assert ch.is_active is True
    assert ch.created_at is not None


def test_channel_unique_constraint(db):
    ch1 = Channel(youtube_channel_id="UC123", name="A", url="url1")
    ch2 = Channel(youtube_channel_id="UC123", name="B", url="url2")
    db.add(ch1)
    db.commit()
    db.add(ch2)
    with pytest.raises(IntegrityError):
        db.commit()


def test_create_video_with_channel(db):
    ch = Channel(youtube_channel_id="UC123", name="Test", url="url")
    db.add(ch)
    db.commit()
    vid = Video(channel_fk=ch.id, youtube_video_id="vid1", title="Video 1", status="pending")
    db.add(vid)
    db.commit()
    assert vid.id is not None
    assert vid.status == "pending"


def test_create_summary(db):
    ch = Channel(youtube_channel_id="UC1", name="C", url="u")
    db.add(ch)
    db.commit()
    vid = Video(channel_fk=ch.id, youtube_video_id="v1", title="T", status="summarized")
    db.add(vid)
    db.commit()
    s = Summary(video_id=vid.id, summary_text="overview", timestamps_json="[]", pdf_path="/tmp/t.pdf")
    db.add(s)
    db.commit()
    assert s.email_sent is False


def test_create_email_config(db):
    ec = EmailConfig(smtp_host="smtp.gmail.com", smtp_port=587, smtp_user="u", smtp_password="p", sender_email="a@b.com", recipients_json='["x@y.com"]')
    db.add(ec)
    db.commit()
    assert ec.is_active is True


def test_create_job_log(db):
    jl = JobLog(action="poll", status="success")
    db.add(jl)
    db.commit()
    assert jl.created_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL

- [ ] **Step 3: Implement database.py and models.py**

`backend/app/database.py`:
```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

class Base(DeclarativeBase):
    pass

def create_db_engine(url: str):
    engine = create_engine(url, connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    return engine

SessionLocal = None

def init_db(url: str):
    global SessionLocal
    engine = create_db_engine(url)
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return engine

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`backend/app/models.py`:
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from app.database import Base


class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    youtube_channel_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    poll_interval_minutes = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    last_polled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_fk = Column(Integer, ForeignKey("channels.id"), nullable=False)
    youtube_video_id = Column(String, unique=True, nullable=False)
    transcript_text = Column(Text, nullable=True)
    title = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Summary(Base):
    __tablename__ = "summaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    summary_text = Column(Text, nullable=False)
    timestamps_json = Column(Text, nullable=False)
    pdf_path = Column(String, nullable=True)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailConfig(Base):
    __tablename__ = "email_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    smtp_host = Column(String, nullable=False)
    smtp_port = Column(Integer, nullable=False)
    smtp_user = Column(String, nullable=False)
    smtp_password = Column(String, nullable=False)
    sender_email = Column(String, nullable=False)
    recipients_json = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)


class JobLog(Base):
    __tablename__ = "job_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_fk = Column(Integer, ForeignKey("channels.id"), nullable=True)
    video_fk = Column(Integer, ForeignKey("videos.id"), nullable=True)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py backend/app/models.py backend/tests/test_models.py
git commit -m "feat: add SQLAlchemy ORM models and database layer"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError
from app.schemas import ChannelCreate, ChannelUpdate, EmailConfigResponse, SummaryResponse


def test_channel_create_valid():
    c = ChannelCreate(url="https://youtube.com/@fireship")
    assert c.poll_interval_minutes == 60


def test_channel_create_missing_url():
    with pytest.raises(ValidationError):
        ChannelCreate()


def test_channel_update_partial():
    u = ChannelUpdate(is_active=False)
    assert u.is_active is False
    assert u.poll_interval_minutes is None


def test_email_config_masks_password():
    r = EmailConfigResponse(
        id=1, smtp_host="smtp.gmail.com", smtp_port=587,
        smtp_user="user", smtp_password="secret123",
        sender_email="a@b.com", recipients=["x@y.com"], is_active=True
    )
    assert r.smtp_password == "******"


def test_summary_response_parses_timestamps():
    s = SummaryResponse(
        id=1, video_id=1, summary_text="overview",
        timestamps=[{"timestamp": "0:00", "title": "Intro", "description": "desc"}],
        pdf_path="/tmp/t.pdf", email_sent=False, created_at="2026-01-01T00:00:00"
    )
    assert len(s.timestamps) == 1
    assert s.timestamps[0]["timestamp"] == "0:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_schemas.py -v`

- [ ] **Step 3: Implement schemas.py**

`backend/app/schemas.py`:
```python
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class ChannelCreate(BaseModel):
    url: str
    poll_interval_minutes: int = 60


class ChannelUpdate(BaseModel):
    poll_interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class ChannelResponse(BaseModel):
    id: int
    youtube_channel_id: str
    name: str
    url: str
    poll_interval_minutes: int
    is_active: bool
    last_polled_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryListItem(BaseModel):
    id: int
    video_id: int
    video_title: str = ""
    channel_name: str = ""
    summary_text: str
    email_sent: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryResponse(BaseModel):
    id: int
    video_id: int
    summary_text: str
    timestamps: list[dict]
    pdf_path: Optional[str] = None
    email_sent: bool
    created_at: datetime


class EmailConfigUpdate(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    sender_email: str
    recipients: list[str]
    is_active: bool = True


class EmailConfigResponse(BaseModel):
    id: int
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str = ""
    sender_email: str
    recipients: list[str]
    is_active: bool

    @field_validator("smtp_password", mode="before")
    @classmethod
    def mask_password(cls, v):
        return "******"


class DashboardResponse(BaseModel):
    channel_count: int
    videos_processed: int
    emails_sent: int
    next_poll_time: Optional[str] = None


class ActivityItem(BaseModel):
    id: int
    action: str
    status: str
    error_message: Optional[str] = None
    video_title: Optional[str] = None
    channel_name: Optional[str] = None
    created_at: datetime
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_schemas.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add Pydantic request/response schemas"
```

---

## Task 4: Channel URL Resolver

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/channel_resolver.py`
- Create: `backend/tests/test_channel_resolver.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_channel_resolver.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.channel_resolver import resolve_channel_id


def test_extract_from_channel_url():
    cid, _ = resolve_channel_id("https://www.youtube.com/channel/UC29ju8bIPH5as8OGnQzwJyA")
    assert cid == "UC29ju8bIPH5as8OGnQzwJyA"


def test_raw_channel_id():
    cid, _ = resolve_channel_id("UC29ju8bIPH5as8OGnQzwJyA")
    assert cid == "UC29ju8bIPH5as8OGnQzwJyA"


@patch("app.services.channel_resolver.httpx.get")
def test_resolve_handle_url(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = '<meta itemprop="identifier" content="UC29ju8bIPH5as8OGnQzwJyA">'
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    cid, _ = resolve_channel_id("https://www.youtube.com/@fireship")
    assert cid == "UC29ju8bIPH5as8OGnQzwJyA"


def test_invalid_url_raises():
    with pytest.raises(ValueError):
        resolve_channel_id("")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_channel_resolver.py -v`

- [ ] **Step 3: Implement channel_resolver.py**

`backend/app/services/channel_resolver.py`:
```python
import re
import httpx


def resolve_channel_id(url_or_id: str) -> tuple[str, str]:
    url_or_id = url_or_id.strip()
    if not url_or_id:
        raise ValueError("Empty channel URL or ID")

    # Raw channel ID
    if re.match(r"^UC[\w-]{22}$", url_or_id):
        return url_or_id, url_or_id

    # /channel/UCxxxx URL
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", url_or_id)
    if m:
        return m.group(1), m.group(1)

    # /@handle or /c/name URL — fetch page to extract channel ID
    if re.search(r"youtube\.com/(@[\w.-]+|c/[\w.-]+)", url_or_id):
        return _fetch_channel_id_from_page(url_or_id)

    raise ValueError(f"Cannot resolve channel from: {url_or_id}")


def _fetch_channel_id_from_page(url: str) -> tuple[str, str]:
    resp = httpx.get(url, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    # Extract channel ID from meta tag
    m = re.search(r'<meta\s+itemprop="identifier"\s+content="(UC[\w-]+)"', resp.text)
    if not m:
        m = re.search(r'"channelId":"(UC[\w-]+)"', resp.text)
    if not m:
        raise ValueError(f"Could not find channel ID in page: {url}")
    channel_id = m.group(1)
    # Try to extract channel name
    name_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', resp.text)
    name = name_match.group(1) if name_match else channel_id
    return channel_id, name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_channel_resolver.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_channel_resolver.py
git commit -m "feat: add channel URL resolver with multiple format support"
```

---

## Task 5: Poller Service (YouTube RSS)

**Files:**
- Create: `backend/app/services/poller.py`
- Create: `backend/tests/test_poller.py`
- Create: `backend/tests/fixtures/sample_rss.xml`

- [ ] **Step 1: Write failing tests**

`backend/tests/fixtures/sample_rss.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
  <title>Test Channel</title>
  <entry>
    <yt:videoId>vid001</yt:videoId>
    <title>First Video</title>
    <published>2026-03-20T10:00:00+00:00</published>
  </entry>
  <entry>
    <yt:videoId>vid002</yt:videoId>
    <title>Second Video</title>
    <published>2026-03-19T10:00:00+00:00</published>
  </entry>
  <entry>
    <yt:videoId>vid003</yt:videoId>
    <title>Third Video</title>
    <published>2026-03-18T10:00:00+00:00</published>
  </entry>
</feed>
```

`backend/tests/test_poller.py`:
```python
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.services.poller import poll_channel

FIXTURE = Path(__file__).parent / "fixtures" / "sample_rss.xml"


@patch("app.services.poller.feedparser.parse")
def test_poll_returns_new_videos(mock_parse):
    import feedparser
    mock_parse.return_value = feedparser.parse(FIXTURE.read_text())
    results = poll_channel("UC123", known_video_ids=set())
    assert len(results) == 3
    assert results[0]["video_id"] == "vid001"
    assert results[0]["title"] == "First Video"


@patch("app.services.poller.feedparser.parse")
def test_poll_filters_known_videos(mock_parse):
    import feedparser
    mock_parse.return_value = feedparser.parse(FIXTURE.read_text())
    results = poll_channel("UC123", known_video_ids={"vid001", "vid003"})
    assert len(results) == 1
    assert results[0]["video_id"] == "vid002"


@patch("app.services.poller.feedparser.parse")
def test_poll_empty_feed(mock_parse):
    mock_parse.return_value = MagicMock(entries=[])
    results = poll_channel("UC123", known_video_ids=set())
    assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_poller.py -v`

- [ ] **Step 3: Implement poller.py**

`backend/app/services/poller.py`:
```python
from datetime import datetime
import feedparser

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def poll_channel(channel_id: str, known_video_ids: set[str]) -> list[dict]:
    url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
    feed = feedparser.parse(url)
    new_videos = []
    for entry in feed.entries:
        video_id = entry.get("yt_videoid", "")
        if video_id and video_id not in known_video_ids:
            published = entry.get("published", "")
            try:
                pub_dt = datetime.fromisoformat(published.replace("+00:00", "+00:00"))
            except (ValueError, AttributeError):
                pub_dt = None
            new_videos.append({
                "video_id": video_id,
                "title": entry.get("title", "Untitled"),
                "published_at": pub_dt,
            })
    return new_videos
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_poller.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/poller.py backend/tests/test_poller.py backend/tests/fixtures/
git commit -m "feat: add YouTube RSS poller service"
```

---

## Task 6: Transcriber Service

**Files:**
- Create: `backend/app/services/transcriber.py`
- Create: `backend/tests/test_transcriber.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_transcriber.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.transcriber import get_transcript, TranscriptUnavailableError


SAMPLE_SEGMENTS = [
    {"text": "Hello everyone", "start": 0.0, "duration": 3.0},
    {"text": "Today we will talk about Python", "start": 3.0, "duration": 4.0},
    {"text": "Let's get started", "start": 65.0, "duration": 2.5},
]


@patch("app.services.transcriber.YouTubeTranscriptApi.get_transcript")
def test_get_transcript_formats_timestamps(mock_api):
    mock_api.return_value = SAMPLE_SEGMENTS
    result = get_transcript("vid001")
    assert "[0:00]" in result
    assert "[0:03]" in result
    assert "[1:05]" in result
    assert "Hello everyone" in result


@patch("app.services.transcriber.YouTubeTranscriptApi.get_transcript")
def test_transcript_unavailable(mock_api):
    from youtube_transcript_api._errors import TranscriptsDisabled
    mock_api.side_effect = TranscriptsDisabled("vid001")
    with pytest.raises(TranscriptUnavailableError):
        get_transcript("vid001")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_transcriber.py -v`

- [ ] **Step 3: Implement transcriber.py**

`backend/app/services/transcriber.py`:
```python
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


class TranscriptUnavailableError(Exception):
    pass


def get_transcript(video_id: str) -> str:
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise TranscriptUnavailableError(f"No transcript for {video_id}: {e}")

    lines = []
    for seg in segments:
        ts = _format_timestamp(seg["start"])
        lines.append(f"[{ts}] {seg['text']}")
    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_transcriber.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/transcriber.py backend/tests/test_transcriber.py
git commit -m "feat: add transcript fetcher service"
```

---

## Task 7: LLM Provider Interface + Grok Implementation

**Files:**
- Create: `backend/app/services/llm/__init__.py`
- Create: `backend/app/services/llm/base.py`
- Create: `backend/app/services/llm/grok_provider.py`
- Create: `backend/app/services/llm/factory.py`
- Create: `backend/tests/test_llm_grok.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_llm_grok.py`:
```python
import json
from unittest.mock import patch, MagicMock
import pytest
from app.services.llm.grok_provider import GrokProvider
from app.services.llm.factory import get_provider


VALID_RESPONSE = json.dumps({
    "summary": "This video covers Python basics.",
    "sections": [
        {"timestamp": "0:00", "title": "Intro", "description": "The host introduces the topic."}
    ]
})


@patch("app.services.llm.grok_provider.OpenAI")
def test_grok_summarize_returns_parsed_json(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_msg = MagicMock()
    mock_msg.content = VALID_RESPONSE
    mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=mock_msg)])

    provider = GrokProvider(api_key="test-key")
    result = provider.summarize("transcript text", "Test Video")
    assert result["summary"] == "This video covers Python basics."
    assert len(result["sections"]) == 1


@patch("app.services.llm.grok_provider.OpenAI")
def test_grok_retries_on_malformed_json(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    bad_msg = MagicMock(content="not json")
    good_msg = MagicMock(content=VALID_RESPONSE)
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=bad_msg)]),
        MagicMock(choices=[MagicMock(message=good_msg)]),
    ]

    provider = GrokProvider(api_key="test-key")
    result = provider.summarize("transcript", "Title")
    assert "summary" in result


def test_factory_returns_grok():
    settings = MagicMock(LLM_PROVIDER="grok", XAI_API_KEY="key")
    provider = get_provider(settings)
    assert isinstance(provider, GrokProvider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_grok.py -v`

- [ ] **Step 3: Implement LLM base, Grok provider, and factory**

`backend/app/services/llm/base.py`:
```python
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def summarize(self, transcript: str, video_title: str) -> dict:
        """Returns {"summary": str, "sections": [{"timestamp", "title", "description"}]}"""
        pass
```

`backend/app/services/llm/grok_provider.py`:
```python
import json
from openai import OpenAI
from app.services.llm.base import LLMProvider

SYSTEM_PROMPT = """You are a video summarizer. Given a transcript with timestamps, produce a JSON object with:
- "summary": A 2-3 sentence overview of the video
- "sections": An array of objects, each with "timestamp" (MM:SS format), "title" (short section title), and "description" (2-3 sentence summary of that segment)

Identify natural topic boundaries. Output ONLY valid JSON, no markdown."""


class GrokProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    def summarize(self, transcript: str, video_title: str) -> dict:
        max_retries = 3
        for attempt in range(max_retries):
            resp = self.client.chat.completions.create(
                model="grok-3",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
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
```

`backend/app/services/llm/factory.py`:
```python
from app.services.llm.base import LLMProvider
from app.services.llm.grok_provider import GrokProvider


def get_provider(settings) -> LLMProvider:
    if settings.LLM_PROVIDER == "grok":
        return GrokProvider(api_key=settings.XAI_API_KEY)
    elif settings.LLM_PROVIDER == "claude":
        from app.services.llm.claude_provider import ClaudeProvider
        return ClaudeProvider(api_key=settings.ANTHROPIC_API_KEY)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_llm_grok.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm/ backend/tests/test_llm_grok.py
git commit -m "feat: add LLM provider interface and Grok implementation"
```

---

## Task 8: Claude Provider Implementation

**Files:**
- Create: `backend/app/services/llm/claude_provider.py`
- Create: `backend/tests/test_llm_claude.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_llm_claude.py`:
```python
import json
from unittest.mock import patch, MagicMock
from app.services.llm.claude_provider import ClaudeProvider
from app.services.llm.factory import get_provider

VALID_RESPONSE = json.dumps({
    "summary": "Overview of the video.",
    "sections": [{"timestamp": "0:00", "title": "Intro", "description": "Desc"}]
})


@patch("app.services.llm.claude_provider.Anthropic")
def test_claude_summarize(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_block = MagicMock(text=VALID_RESPONSE)
    mock_client.messages.create.return_value = MagicMock(content=[mock_block])

    provider = ClaudeProvider(api_key="test-key")
    result = provider.summarize("transcript", "Title")
    assert result["summary"] == "Overview of the video."


def test_factory_returns_claude():
    settings = MagicMock(LLM_PROVIDER="claude", ANTHROPIC_API_KEY="key")
    provider = get_provider(settings)
    assert isinstance(provider, ClaudeProvider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_claude.py -v`

- [ ] **Step 3: Implement claude_provider.py**

`backend/app/services/llm/claude_provider.py`:
```python
import json
from anthropic import Anthropic
from app.services.llm.base import LLMProvider

SYSTEM_PROMPT = """You are a video summarizer. Given a transcript with timestamps, produce a JSON object with:
- "summary": A 2-3 sentence overview of the video
- "sections": An array of objects, each with "timestamp" (MM:SS format), "title" (short section title), and "description" (2-3 sentence summary of that segment)

Identify natural topic boundaries. Output ONLY valid JSON, no markdown."""


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def summarize(self, transcript: str, video_title: str) -> dict:
        max_retries = 3
        for attempt in range(max_retries):
            resp = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_llm_claude.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm/claude_provider.py backend/tests/test_llm_claude.py
git commit -m "feat: add Claude Opus LLM provider"
```

---

## Task 9: Summarizer Service (Chunking + LLM)

**Files:**
- Create: `backend/app/services/summarizer.py`
- Create: `backend/tests/test_summarizer.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_summarizer.py`:
```python
from unittest.mock import MagicMock
from app.services.summarizer import summarize_transcript


def test_short_transcript_single_pass():
    provider = MagicMock()
    provider.summarize.return_value = {
        "summary": "Short overview",
        "sections": [{"timestamp": "0:00", "title": "All", "description": "Everything"}]
    }
    result = summarize_transcript("short transcript", "Title", provider)
    assert result["summary"] == "Short overview"
    provider.summarize.assert_called_once()


def test_long_transcript_triggers_chunking():
    provider = MagicMock()
    provider.summarize.return_value = {
        "summary": "Chunk summary",
        "sections": [{"timestamp": "0:00", "title": "Part", "description": "Desc"}]
    }
    # Create a transcript longer than the token limit
    long_transcript = "\n".join([f"[{i}:00] word " * 100 for i in range(200)])
    result = summarize_transcript(long_transcript, "Title", provider, max_tokens=1000)
    assert provider.summarize.call_count > 1
    assert "summary" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_summarizer.py -v`

- [ ] **Step 3: Implement summarizer.py**

`backend/app/services/summarizer.py`:
```python
import re
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

    # Use the last chunk's summary call to merge
    summaries_text = "\n".join(cr.get("summary", "") for cr in chunk_results)
    merge_input = f"Combine these partial summaries into one cohesive summary:\n{summaries_text}"
    merged = provider.summarize(merge_input, video_title)
    merged["sections"] = all_sections
    return merged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_summarizer.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/summarizer.py backend/tests/test_summarizer.py
git commit -m "feat: add summarizer service with chunking support"
```

---

## Task 10: PDF Generator Service

**Files:**
- Create: `backend/app/services/pdf_generator.py`
- Create: `backend/tests/test_pdf_generator.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_pdf_generator.py`:
```python
from datetime import datetime
from pathlib import Path
from app.services.pdf_generator import generate_pdf


def test_pdf_is_created(tmp_path):
    path = generate_pdf(
        video_title="Test Video",
        channel_name="Test Channel",
        published_at=datetime(2026, 3, 25),
        video_url="https://youtube.com/watch?v=abc",
        summary="This is a test summary of the video.",
        sections=[
            {"timestamp": "0:00", "title": "Intro", "description": "The intro section."},
            {"timestamp": "5:30", "title": "Main", "description": "Main content here."},
        ],
        output_dir=str(tmp_path),
    )
    assert Path(path).exists()


def test_pdf_is_valid(tmp_path):
    path = generate_pdf(
        video_title="Test",
        channel_name="Ch",
        published_at=datetime(2026, 1, 1),
        video_url="https://youtube.com/watch?v=x",
        summary="Summary.",
        sections=[],
        output_dir=str(tmp_path),
    )
    with open(path, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_special_characters_in_title(tmp_path):
    path = generate_pdf(
        video_title="What's New? C++ / 2026!",
        channel_name="Dev Ch",
        published_at=datetime(2026, 1, 1),
        video_url="url",
        summary="S",
        sections=[],
        output_dir=str(tmp_path),
    )
    assert Path(path).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_pdf_generator.py -v`

- [ ] **Step 3: Implement pdf_generator.py**

`backend/app/services/pdf_generator.py`:
```python
import re
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.colors import HexColor


def generate_pdf(
    video_title: str,
    channel_name: str,
    published_at: datetime,
    video_url: str,
    summary: str,
    sections: list[dict],
    output_dir: str,
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    safe_title = re.sub(r'[^\w\s-]', '', video_title)[:50].strip()
    filename = f"{safe_title}_{published_at.strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                  fontSize=18, spaceAfter=6)
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'],
                                 fontSize=10, textColor=HexColor('#666666'))
    section_title_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'],
                                          fontSize=14, spaceBefore=12)
    body_style = styles['BodyText']
    timestamp_style = ParagraphStyle('Timestamp', parent=styles['Normal'],
                                      fontSize=10, textColor=HexColor('#0066cc'),
                                      spaceBefore=8)

    elements = []

    # Header
    elements.append(Paragraph(_escape(video_title), title_style))
    elements.append(Paragraph(f"{_escape(channel_name)} | {published_at.strftime('%B %d, %Y')}", meta_style))
    elements.append(Paragraph(f"<link href='{video_url}'>{_escape(video_url)}</link>", meta_style))
    elements.append(Spacer(1, 12))

    # Summary
    elements.append(Paragraph("<b>Summary</b>", styles['Heading2']))
    elements.append(Paragraph(_escape(summary), body_style))
    elements.append(Spacer(1, 12))

    # Timestamped sections
    if sections:
        elements.append(Paragraph("<b>Timestamps</b>", styles['Heading2']))
        for sec in sections:
            ts = sec.get("timestamp", "")
            title = sec.get("title", "")
            desc = sec.get("description", "")
            elements.append(Paragraph(f"<b>{_escape(ts)} — {_escape(title)}</b>", section_title_style))
            elements.append(Paragraph(_escape(desc), body_style))

    # Footer
    elements.append(Spacer(1, 24))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
                                   fontSize=8, textColor=HexColor('#999999'))
    elements.append(Paragraph(
        f"Generated by YT Summarizer on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        footer_style
    ))

    doc.build(elements)
    return filepath


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_pdf_generator.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pdf_generator.py backend/tests/test_pdf_generator.py
git commit -m "feat: add ReportLab PDF generator service"
```

---

## Task 11: Email Service

**Files:**
- Create: `backend/app/services/emailer.py`
- Create: `backend/tests/test_emailer.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_emailer.py`:
```python
from unittest.mock import patch, MagicMock
from app.services.emailer import encrypt_password, decrypt_password, send_summary_email


def test_encrypt_decrypt_roundtrip():
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    encrypted = encrypt_password("my_secret", key)
    assert encrypted != "my_secret"
    decrypted = decrypt_password(encrypted, key)
    assert decrypted == "my_secret"


@patch("app.services.emailer.smtplib.SMTP")
def test_send_email_calls_smtp(mock_smtp_cls, tmp_path):
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    # Create a dummy PDF
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test content")

    send_summary_email(
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        sender_email="sender@test.com",
        recipients=["recipient@test.com"],
        video_title="Test Video",
        channel_name="Test Channel",
        summary_text="A summary",
        video_url="https://youtube.com/watch?v=abc",
        pdf_path=str(pdf_path),
    )
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("user", "pass")
    mock_smtp.send_message.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_emailer.py -v`

- [ ] **Step 3: Implement emailer.py**

`backend/app/services/emailer.py`:
```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from cryptography.fernet import Fernet


def encrypt_password(plain: str, key: str) -> str:
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(plain.encode()).decode()


def decrypt_password(cipher: str, key: str) -> str:
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.decrypt(cipher.encode()).decode()


def send_summary_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    sender_email: str,
    recipients: list[str],
    video_title: str,
    channel_name: str,
    summary_text: str,
    video_url: str,
    pdf_path: str,
) -> None:
    subject = f"[YT Summary] {video_title} — {channel_name}"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    body = f"""New video summary available!

Video: {video_title}
Channel: {channel_name}
Link: {video_url}

Summary:
{summary_text}

Full timestamped summary attached as PDF.
"""
    msg.attach(MIMEText(body, "plain"))

    # Attach PDF
    pdf_file = Path(pdf_path)
    if pdf_file.exists():
        with open(pdf_file, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header("Content-Disposition", "attachment", filename=pdf_file.name)
            msg.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_emailer.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/emailer.py backend/tests/test_emailer.py
git commit -m "feat: add SMTP email service with encrypted password storage"
```

---

## Task 12: Job Logger + Pipeline Orchestrator

**Files:**
- Create: `backend/app/services/job_logger.py`
- Create: `backend/app/services/pipeline.py`
- Create: `backend/tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_pipeline.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Channel, Video
from app.services.pipeline import process_channel


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_happy_path(db):
    ch = Channel(youtube_channel_id="UC1", name="Ch", url="u", poll_interval_minutes=60)
    db.add(ch)
    db.commit()

    settings = MagicMock(PDF_DIR="/tmp/pdfs", ENCRYPTION_KEY="testkey")
    provider = MagicMock()
    provider.summarize.return_value = {
        "summary": "Overview",
        "sections": [{"timestamp": "0:00", "title": "Intro", "description": "Desc"}]
    }

    with patch("app.services.pipeline.poll_channel") as mock_poll, \
         patch("app.services.pipeline.get_transcript") as mock_transcript, \
         patch("app.services.pipeline.generate_pdf") as mock_pdf, \
         patch("app.services.pipeline.send_email_for_video") as mock_email:

        mock_poll.return_value = [{"video_id": "v1", "title": "Vid", "published_at": datetime.utcnow()}]
        mock_transcript.return_value = "[0:00] Hello"
        mock_pdf.return_value = "/tmp/test.pdf"

        process_channel(ch.id, db, settings, provider)

    vid = db.query(Video).filter_by(youtube_video_id="v1").first()
    assert vid is not None
    assert vid.status == "summarized"


def test_transcript_failure_marks_failed(db):
    ch = Channel(youtube_channel_id="UC2", name="Ch2", url="u2")
    db.add(ch)
    db.commit()

    settings = MagicMock(PDF_DIR="/tmp/pdfs", ENCRYPTION_KEY="k")
    provider = MagicMock()

    with patch("app.services.pipeline.poll_channel") as mock_poll, \
         patch("app.services.pipeline.get_transcript") as mock_transcript:

        mock_poll.return_value = [{"video_id": "v2", "title": "V2", "published_at": None}]
        from app.services.transcriber import TranscriptUnavailableError
        mock_transcript.side_effect = TranscriptUnavailableError("no captions")

        process_channel(ch.id, db, settings, provider)

    vid = db.query(Video).filter_by(youtube_video_id="v2").first()
    assert vid.status == "failed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`

- [ ] **Step 3: Implement job_logger.py and pipeline.py**

`backend/app/services/job_logger.py`:
```python
from sqlalchemy.orm import Session
from app.models import JobLog


def log_job(db: Session, action: str, status: str,
            channel_id: int = None, video_id: int = None, error: str = None) -> JobLog:
    entry = JobLog(
        channel_fk=channel_id,
        video_fk=video_id,
        action=action,
        status=status,
        error_message=error,
    )
    db.add(entry)
    db.commit()
    return entry
```

`backend/app/services/pipeline.py`:
```python
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Channel, Video, Summary, EmailConfig
from app.services.poller import poll_channel
from app.services.transcriber import get_transcript, TranscriptUnavailableError
from app.services.summarizer import summarize_transcript
from app.services.pdf_generator import generate_pdf
from app.services.emailer import send_summary_email, decrypt_password
from app.services.job_logger import log_job

logger = logging.getLogger(__name__)


def process_channel(channel_id: int, db: Session, settings, provider) -> None:
    channel = db.query(Channel).get(channel_id)
    if not channel:
        return

    # Poll for new videos
    known_ids = {v.youtube_video_id for v in db.query(Video.youtube_video_id).filter_by(channel_fk=channel_id)}
    try:
        new_videos = poll_channel(channel.youtube_channel_id, known_ids)
        log_job(db, "poll", "success", channel_id=channel_id)
    except Exception as e:
        log_job(db, "poll", "failed", channel_id=channel_id, error=str(e))
        logger.error(f"Poll failed for channel {channel_id}: {e}")
        return

    channel.last_polled_at = datetime.utcnow()
    db.commit()

    for vdata in new_videos:
        vid = Video(
            channel_fk=channel_id,
            youtube_video_id=vdata["video_id"],
            title=vdata["title"],
            published_at=vdata.get("published_at"),
            status="pending",
        )
        db.add(vid)
        db.commit()
        _process_video(vid, channel, db, settings, provider)


def _process_video(video: Video, channel: Channel, db: Session, settings, provider) -> None:
    # Fetch transcript
    try:
        transcript = get_transcript(video.youtube_video_id)
        video.transcript_text = transcript
        db.commit()
        log_job(db, "transcribe", "success", channel_id=channel.id, video_id=video.id)
    except TranscriptUnavailableError as e:
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        log_job(db, "transcribe", "failed", channel_id=channel.id, video_id=video.id, error=str(e))
        return

    # Summarize
    try:
        result = summarize_transcript(transcript, video.title, provider)
        log_job(db, "summarize", "success", channel_id=channel.id, video_id=video.id)
    except Exception as e:
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        log_job(db, "summarize", "failed", channel_id=channel.id, video_id=video.id, error=str(e))
        return

    # Generate PDF
    try:
        pdf_path = generate_pdf(
            video_title=video.title,
            channel_name=channel.name,
            published_at=video.published_at or datetime.utcnow(),
            video_url=f"https://youtube.com/watch?v={video.youtube_video_id}",
            summary=result["summary"],
            sections=result.get("sections", []),
            output_dir=settings.PDF_DIR,
        )
        log_job(db, "pdf", "success", channel_id=channel.id, video_id=video.id)
    except Exception as e:
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        log_job(db, "pdf", "failed", channel_id=channel.id, video_id=video.id, error=str(e))
        return

    # Save summary
    summary = Summary(
        video_id=video.id,
        summary_text=result["summary"],
        timestamps_json=json.dumps(result.get("sections", [])),
        pdf_path=pdf_path,
    )
    db.add(summary)
    video.status = "summarized"
    db.commit()

    # Send email
    send_email_for_video(video, channel, summary, result, db, settings)


def send_email_for_video(video, channel, summary, result, db, settings):
    email_config = db.query(EmailConfig).first()
    if not email_config or not email_config.is_active:
        return

    try:
        recipients = json.loads(email_config.recipients_json)
        password = decrypt_password(email_config.smtp_password, settings.ENCRYPTION_KEY)
        send_summary_email(
            smtp_host=email_config.smtp_host,
            smtp_port=email_config.smtp_port,
            smtp_user=email_config.smtp_user,
            smtp_password=password,
            sender_email=email_config.sender_email,
            recipients=recipients,
            video_title=video.title,
            channel_name=channel.name,
            summary_text=result["summary"],
            video_url=f"https://youtube.com/watch?v={video.youtube_video_id}",
            pdf_path=summary.pdf_path,
        )
        summary.email_sent = True
        db.commit()
        log_job(db, "email", "success", channel_id=channel.id, video_id=video.id)
    except Exception as e:
        log_job(db, "email", "failed", channel_id=channel.id, video_id=video.id, error=str(e))
        logger.error(f"Email failed for video {video.id}: {e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/job_logger.py backend/app/services/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator and job logger"
```

---

## Task 13: Scheduler Service

**Files:**
- Create: `backend/app/services/scheduler.py`
- Create: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_scheduler.py`:
```python
from unittest.mock import MagicMock, patch
from app.services.scheduler import register_channel_job, remove_channel_job


def test_register_adds_interval_job():
    sched = MagicMock()
    channel = MagicMock(id=1, poll_interval_minutes=30, youtube_channel_id="UC1")
    register_channel_job(sched, channel, MagicMock(), MagicMock(), MagicMock())
    sched.add_job.assert_called_once()
    call_kwargs = sched.add_job.call_args
    assert call_kwargs.kwargs.get("minutes") == 30 or call_kwargs[1].get("minutes") == 30


def test_remove_job():
    sched = MagicMock()
    remove_channel_job(sched, 1)
    sched.remove_job.assert_called_once_with("channel_1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_scheduler.py -v`

- [ ] **Step 3: Implement scheduler.py**

`backend/app/services/scheduler.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.models import Channel, Video
from app.services.pipeline import process_channel


def create_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler()


def register_channel_job(scheduler, channel, db_factory, settings, provider):
    job_id = f"channel_{channel.id}"
    scheduler.add_job(
        _run_pipeline,
        "interval",
        minutes=channel.poll_interval_minutes,
        id=job_id,
        args=[channel.id, db_factory, settings, provider],
        replace_existing=True,
    )


def remove_channel_job(scheduler, channel_id: int):
    job_id = f"channel_{channel_id}"
    scheduler.remove_job(job_id)


def reschedule_channel_job(scheduler, channel, db_factory, settings, provider):
    remove_channel_job(scheduler, channel.id)
    if channel.is_active:
        register_channel_job(scheduler, channel, db_factory, settings, provider)


def startup_register_all(scheduler, db: Session, db_factory, settings, provider):
    channels = db.query(Channel).filter_by(is_active=True).all()
    for ch in channels:
        register_channel_job(scheduler, ch, db_factory, settings, provider)

    # Re-queue pending videos
    pending = db.query(Video).filter_by(status="pending").all()
    for vid in pending:
        channel = db.query(Channel).get(vid.channel_fk)
        if channel:
            from app.services.pipeline import _process_video
            _process_video(vid, channel, db, settings, provider)


def _run_pipeline(channel_id: int, db_factory, settings, provider):
    db = db_factory()
    try:
        process_channel(channel_id, db, settings, provider)
    finally:
        db.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_scheduler.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat: add APScheduler service for channel polling"
```

---

## Task 14: FastAPI App + API Endpoints

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/channels.py`
- Create: `backend/app/api/summaries.py`
- Create: `backend/app/api/email.py`
- Create: `backend/app/api/dashboard.py`
- Create: `backend/tests/test_api_channels.py`
- Create: `backend/tests/test_api_summaries.py`
- Create: `backend/tests/test_api_email.py`
- Create: `backend/tests/test_api_dashboard.py`

- [ ] **Step 1: Implement main.py with lifespan and router registration**

`backend/app/main.py`:
```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import Settings
from app.database import init_db, SessionLocal
from app.services.scheduler import create_scheduler, startup_register_all
from app.services.llm.factory import get_provider

settings = Settings()
scheduler = None
provider = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler, provider
    engine = init_db(settings.DATABASE_URL)
    os.makedirs(settings.PDF_DIR, exist_ok=True)

    provider = get_provider(settings)
    scheduler = create_scheduler()

    db = SessionLocal()
    try:
        startup_register_all(scheduler, db, SessionLocal, settings, provider)
    finally:
        db.close()

    scheduler.start()
    yield
    scheduler.shutdown(wait=True)


app = FastAPI(title="YT Summarizer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import channels, summaries, email, dashboard
app.include_router(channels.router)
app.include_router(summaries.router)
app.include_router(email.router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve frontend static files in production
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

- [ ] **Step 2: Implement channels router**

`backend/app/api/channels.py`:
```python
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Channel, Video
from app.schemas import ChannelCreate, ChannelUpdate, ChannelResponse
from app.services.channel_resolver import resolve_channel_id

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("", response_model=list[ChannelResponse])
def list_channels(db: Session = Depends(get_db)):
    return db.query(Channel).all()


@router.post("", response_model=ChannelResponse, status_code=201)
def add_channel(data: ChannelCreate, db: Session = Depends(get_db)):
    try:
        channel_id, name = resolve_channel_id(data.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    existing = db.query(Channel).filter_by(youtube_channel_id=channel_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Channel already exists")
    ch = Channel(
        youtube_channel_id=channel_id, name=name, url=data.url,
        poll_interval_minutes=data.poll_interval_minutes,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    # Register scheduler job (imported from main at runtime to avoid circular import)
    from app.main import scheduler, settings, provider
    from app.services.scheduler import register_channel_job
    from app.database import SessionLocal
    register_channel_job(scheduler, ch, SessionLocal, settings, provider)
    return ch


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(channel_id: int, data: ChannelUpdate, db: Session = Depends(get_db)):
    ch = db.query(Channel).get(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    if data.poll_interval_minutes is not None:
        ch.poll_interval_minutes = data.poll_interval_minutes
    if data.is_active is not None:
        ch.is_active = data.is_active
    db.commit()
    db.refresh(ch)
    from app.main import scheduler, settings, provider
    from app.services.scheduler import reschedule_channel_job
    from app.database import SessionLocal
    reschedule_channel_job(scheduler, ch, SessionLocal, settings, provider)
    return ch


@router.delete("/{channel_id}", status_code=204)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    ch = db.query(Channel).get(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    from app.main import scheduler
    from app.services.scheduler import remove_channel_job
    try:
        remove_channel_job(scheduler, channel_id)
    except Exception:
        pass
    db.delete(ch)
    db.commit()


@router.post("/{channel_id}/poll")
def force_poll(channel_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    ch = db.query(Channel).get(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    from app.main import settings, provider
    from app.database import SessionLocal
    from app.services.pipeline import process_channel
    background_tasks.add_task(process_channel, channel_id, SessionLocal(), settings, provider)
    return {"status": "polling started"}
```

- [ ] **Step 3: Implement summaries router**

`backend/app/api/summaries.py`:
```python
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Summary, Video, Channel
from app.schemas import SummaryResponse, SummaryListItem

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.get("")
def list_summaries(channel_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Summary, Video, Channel).join(Video, Summary.video_id == Video.id).join(Channel, Video.channel_fk == Channel.id)
    if channel_id:
        query = query.filter(Video.channel_fk == channel_id)
    results = query.order_by(Summary.created_at.desc()).all()
    return [
        {
            "id": s.id, "video_id": s.video_id, "video_title": v.title,
            "channel_name": c.name, "summary_text": s.summary_text,
            "email_sent": s.email_sent, "created_at": s.created_at,
        }
        for s, v, c in results
    ]


@router.get("/{summary_id}")
def get_summary(summary_id: int, db: Session = Depends(get_db)):
    s = db.query(Summary).get(summary_id)
    if not s:
        raise HTTPException(status_code=404, detail="Summary not found")
    return {
        "id": s.id, "video_id": s.video_id, "summary_text": s.summary_text,
        "timestamps": json.loads(s.timestamps_json),
        "pdf_path": s.pdf_path, "email_sent": s.email_sent, "created_at": s.created_at,
    }


@router.get("/{summary_id}/pdf")
def download_pdf(summary_id: int, db: Session = Depends(get_db)):
    s = db.query(Summary).get(summary_id)
    if not s or not s.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(s.pdf_path, media_type="application/pdf", filename=s.pdf_path.split("/")[-1])


@router.post("/{summary_id}/resend")
def resend_email(summary_id: int, db: Session = Depends(get_db)):
    s = db.query(Summary).get(summary_id)
    if not s:
        raise HTTPException(status_code=404, detail="Summary not found")
    video = db.query(Video).get(s.video_id)
    channel = db.query(Channel).get(video.channel_fk)
    from app.main import settings
    from app.services.pipeline import send_email_for_video
    result = {"summary": s.summary_text, "sections": json.loads(s.timestamps_json)}
    send_email_for_video(video, channel, s, result, db, settings)
    return {"status": "email sent"}


@router.post("/{summary_id}/regenerate")
def regenerate_summary(summary_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    s = db.query(Summary).get(summary_id)
    if not s:
        raise HTTPException(status_code=404, detail="Summary not found")
    video = db.query(Video).get(s.video_id)
    if not video.transcript_text:
        raise HTTPException(status_code=400, detail="No cached transcript")
    from app.main import settings, provider
    from app.services.pipeline import _process_video
    channel = db.query(Channel).get(video.channel_fk)
    video.status = "pending"
    db.delete(s)
    db.commit()
    background_tasks.add_task(_process_video, video, channel, db, settings, provider)
    return {"status": "regenerating"}
```

- [ ] **Step 4: Implement email config router**

`backend/app/api/email.py`:
```python
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import EmailConfig
from app.schemas import EmailConfigUpdate, EmailConfigResponse
from app.services.emailer import encrypt_password, send_summary_email

router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("")
def get_email_config(db: Session = Depends(get_db)):
    config = db.query(EmailConfig).first()
    if not config:
        return None
    return {
        "id": config.id, "smtp_host": config.smtp_host, "smtp_port": config.smtp_port,
        "smtp_user": config.smtp_user, "smtp_password": "******",
        "sender_email": config.sender_email,
        "recipients": json.loads(config.recipients_json), "is_active": config.is_active,
    }


@router.put("")
def update_email_config(data: EmailConfigUpdate, db: Session = Depends(get_db)):
    from app.main import settings
    config = db.query(EmailConfig).first()
    encrypted_pw = encrypt_password(data.smtp_password, settings.ENCRYPTION_KEY)
    if config:
        config.smtp_host = data.smtp_host
        config.smtp_port = data.smtp_port
        config.smtp_user = data.smtp_user
        config.smtp_password = encrypted_pw
        config.sender_email = data.sender_email
        config.recipients_json = json.dumps(data.recipients)
        config.is_active = data.is_active
    else:
        config = EmailConfig(
            smtp_host=data.smtp_host, smtp_port=data.smtp_port,
            smtp_user=data.smtp_user, smtp_password=encrypted_pw,
            sender_email=data.sender_email,
            recipients_json=json.dumps(data.recipients), is_active=data.is_active,
        )
        db.add(config)
    db.commit()
    return {"status": "updated"}


@router.post("/test")
def send_test_email(db: Session = Depends(get_db)):
    from app.main import settings
    from app.services.emailer import decrypt_password
    config = db.query(EmailConfig).first()
    if not config:
        raise HTTPException(status_code=400, detail="Email not configured")
    recipients = json.loads(config.recipients_json)
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients configured")
    password = decrypt_password(config.smtp_password, settings.ENCRYPTION_KEY)
    send_summary_email(
        smtp_host=config.smtp_host, smtp_port=config.smtp_port,
        smtp_user=config.smtp_user, smtp_password=password,
        sender_email=config.sender_email, recipients=[recipients[0]],
        video_title="Test Email", channel_name="YT Summarizer",
        summary_text="This is a test email from YT Summarizer.",
        video_url="https://youtube.com", pdf_path="",
    )
    return {"status": "test email sent"}
```

- [ ] **Step 5: Implement dashboard router**

`backend/app/api/dashboard.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Channel, Video, Summary, JobLog

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    channel_count = db.query(func.count(Channel.id)).scalar()
    videos_processed = db.query(func.count(Video.id)).filter(Video.status == "summarized").scalar()
    emails_sent = db.query(func.count(Summary.id)).filter(Summary.email_sent == True).scalar()
    return {
        "channel_count": channel_count,
        "videos_processed": videos_processed,
        "emails_sent": emails_sent,
        "next_poll_time": None,
    }


@router.get("/activity")
def get_activity(limit: int = 20, db: Session = Depends(get_db)):
    logs = db.query(JobLog).order_by(JobLog.created_at.desc()).limit(limit).all()
    results = []
    for log in logs:
        video_title = None
        channel_name = None
        if log.video_fk:
            from app.models import Video
            vid = db.query(Video).get(log.video_fk)
            if vid:
                video_title = vid.title
        if log.channel_fk:
            ch = db.query(Channel).get(log.channel_fk)
            if ch:
                channel_name = ch.name
        results.append({
            "id": log.id, "action": log.action, "status": log.status,
            "error_message": log.error_message, "video_title": video_title,
            "channel_name": channel_name, "created_at": log.created_at,
        })
    return results
```

- [ ] **Step 6: Write API tests**

`backend/tests/test_api_channels.py`:
```python
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.database import get_db

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


# Patch scheduler/settings/provider before importing app
with patch("app.main.scheduler", MagicMock()), \
     patch("app.main.settings", MagicMock(ENCRYPTION_KEY="testkey")), \
     patch("app.main.provider", MagicMock()):
    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)


@patch("app.api.channels.resolve_channel_id", return_value=("UC123", "Test Channel"))
@patch("app.api.channels.register_channel_job")
def test_add_channel(mock_sched, mock_resolve):
    resp = client.post("/api/channels", json={"url": "https://youtube.com/@test"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test Channel"


def test_list_channels():
    resp = client.get("/api/channels")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

Create similar test files for summaries, email, and dashboard endpoints.

- [ ] **Step 4: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/app/api/ backend/tests/test_api_*.py
git commit -m "feat: add FastAPI app with all API endpoints"
```

---

## Task 15: Frontend Scaffold

**Files:**
- Create: `frontend/` (via Vite)
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/types.ts`

- [ ] **Step 1: Initialize Vite React TypeScript project**

```bash
cd "C:/Users/22317/Documents/Coding/Youtube video summarizer"
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
npm install axios react-router-dom
```

- [ ] **Step 2: Set up routing, layout, sidebar, and API client**

Configure `vite.config.ts` with proxy to backend, create Layout with sidebar nav (Dashboard, Channels, Summaries, Email Settings), create placeholder pages, create Axios client.

- [ ] **Step 3: Verify app renders**

Run: `cd frontend && npm run dev`
Expected: App loads at localhost:5173 with sidebar navigation

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React frontend with routing and layout"
```

---

## Task 16: Frontend Pages

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Channels.tsx`
- Modify: `frontend/src/pages/Summaries.tsx`
- Modify: `frontend/src/pages/EmailSettings.tsx`
- Create: `frontend/src/api/channels.ts`
- Create: `frontend/src/api/summaries.ts`
- Create: `frontend/src/api/email.ts`
- Create: `frontend/src/api/dashboard.ts`
- Create: `frontend/src/components/StatsCard.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`

- [ ] **Step 1: Implement API client functions**

Type-safe Axios wrappers for all backend endpoints.

- [ ] **Step 2: Implement Dashboard page**

Stats cards + activity feed, matching the mockup design.

- [ ] **Step 3: Implement Channels page**

Channel table + add form + per-row actions.

- [ ] **Step 4: Implement Summaries page**

Summary list + filter + expandable detail view + action buttons.

- [ ] **Step 5: Implement Email Settings page**

SMTP form + recipient list + test email + toggle.

- [ ] **Step 6: Verify all pages work against running backend**

Run backend + frontend dev server, test all CRUD flows manually.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: implement all frontend pages"
```

---

## Task 17: Build Integration + Deployment

**Files:**
- Create: `build.sh`
- Create: `Procfile`
- Create: `railway.toml`
- Create: `runtime.txt`

- [ ] **Step 1: Create build script**

`build.sh`:
```bash
#!/bin/bash
cd frontend && npm install && npm run build
mkdir -p ../backend/app/static
cp -r dist/* ../backend/app/static/
```

- [ ] **Step 2: Create Railway config files**

`Procfile`:
```
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`railway.toml`:
```toml
[build]
builder = "nixpacks"
buildCommand = "bash build.sh && cd backend && pip install -r requirements.txt"

[deploy]
startCommand = "cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"

[[volumes]]
mount = "/data"
```

`runtime.txt`:
```
python-3.11
```

- [ ] **Step 3: Test build locally**

Run: `bash build.sh && cd backend && uvicorn app.main:app`
Expected: App serves at localhost:8000 with frontend and API working

- [ ] **Step 4: Commit**

```bash
git add build.sh Procfile railway.toml runtime.txt
git commit -m "feat: add Railway deployment configuration"
```

---

## Task 18: README + Final Smoke Test

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

Include: project overview, prerequisites (Python 3.11+, Node 18+, Ollama optional), local dev setup, environment variables, running tests, Railway deployment steps.

- [ ] **Step 2: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --cov=app`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and deployment instructions"
```
