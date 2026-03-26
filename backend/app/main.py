import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app import database
from app.database import init_db
from app.services.scheduler import create_scheduler, startup_register_all
from app.services.llm.factory import get_provider

logger = logging.getLogger(__name__)

# Module-level globals that routers import at call time
scheduler = None
settings = None
provider = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler, settings, provider

    settings = Settings()
    init_db(settings.DATABASE_URL)
    provider = get_provider(settings)
    scheduler = create_scheduler()

    db = database.SessionLocal()
    try:
        startup_register_all(scheduler, db, database.SessionLocal, settings, provider)
    finally:
        db.close()

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))

    yield

    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")


app = FastAPI(title="YouTube Video Summarizer", lifespan=lifespan)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api.channels import router as channels_router
from app.api.summaries import router as summaries_router
from app.api.email import router as email_router
from app.api.dashboard import router as dashboard_router
from app.api.llm_settings import router as llm_settings_router

app.include_router(channels_router)
app.include_router(summaries_router)
app.include_router(email_router)
app.include_router(dashboard_router)
app.include_router(llm_settings_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# Mount static files for production frontend build
# In Railway deployment, build.sh copies frontend into app/static/
# In local dev, frontend/dist is used directly
static_dir = os.path.join(os.path.dirname(__file__), "static")
frontend_build = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
elif frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="static")
