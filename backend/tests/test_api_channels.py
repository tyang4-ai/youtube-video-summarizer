import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Channel


@pytest.fixture
def test_app():
    """Create a standalone FastAPI app with test DB, no lifespan."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    # Create a fresh app without lifespan to avoid real init_db/scheduler
    test_app = FastAPI()

    from app.api.channels import router as channels_router
    from app.api.summaries import router as summaries_router
    from app.api.email import router as email_router
    from app.api.dashboard import router as dashboard_router

    test_app.include_router(channels_router)
    test_app.include_router(summaries_router)
    test_app.include_router(email_router)
    test_app.include_router(dashboard_router)

    @test_app.get("/api/health")
    def health_check():
        return {"status": "ok"}

    test_app.dependency_overrides[get_db] = override_get_db

    # Patch the globals that the routers import from app.main at call time
    with patch("app.main.scheduler", MagicMock()), \
         patch("app.main.settings", MagicMock()), \
         patch("app.main.provider", MagicMock()), \
         patch("app.database.SessionLocal", TestSession):
        client = TestClient(test_app)
        yield client

    test_app.dependency_overrides.clear()


def test_health_check(test_app):
    resp = test_app.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_channels_empty(test_app):
    resp = test_app.get("/api/channels")
    assert resp.status_code == 200
    assert resp.json() == []


@patch("app.api.channels.resolve_channel_id")
def test_add_channel(mock_resolve, test_app):
    mock_resolve.return_value = ("UCxxxxxxxxxxxxxxxxxxxxxx", "My Channel")

    resp = test_app.post(
        "/api/channels",
        json={"url": "https://youtube.com/@mychannel", "poll_interval_minutes": 30},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["youtube_channel_id"] == "UCxxxxxxxxxxxxxxxxxxxxxx"
    assert data["name"] == "My Channel"
    assert data["poll_interval_minutes"] == 30
    assert data["is_active"] is True


@patch("app.api.channels.resolve_channel_id")
def test_add_channel_duplicate(mock_resolve, test_app):
    mock_resolve.return_value = ("UCduplicate_channel_id_12", "Dup Channel")

    resp1 = test_app.post(
        "/api/channels",
        json={"url": "https://youtube.com/@dup"},
    )
    assert resp1.status_code == 201

    resp2 = test_app.post(
        "/api/channels",
        json={"url": "https://youtube.com/@dup"},
    )
    assert resp2.status_code == 409


@patch("app.api.channels.resolve_channel_id")
def test_add_channel_invalid_url(mock_resolve, test_app):
    mock_resolve.side_effect = ValueError("Cannot resolve channel")

    resp = test_app.post(
        "/api/channels",
        json={"url": "not-a-url"},
    )
    assert resp.status_code == 400


@patch("app.api.channels.resolve_channel_id")
def test_update_channel(mock_resolve, test_app):
    mock_resolve.return_value = ("UCupdate_channel_test_1234", "Update Channel")

    resp = test_app.post(
        "/api/channels",
        json={"url": "https://youtube.com/@update"},
    )
    assert resp.status_code == 201
    channel_id = resp.json()["id"]

    resp = test_app.put(
        f"/api/channels/{channel_id}",
        json={"poll_interval_minutes": 120, "is_active": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["poll_interval_minutes"] == 120
    assert data["is_active"] is False


def test_update_channel_not_found(test_app):
    resp = test_app.put(
        "/api/channels/999",
        json={"poll_interval_minutes": 10},
    )
    assert resp.status_code == 404


@patch("app.api.channels.resolve_channel_id")
def test_delete_channel(mock_resolve, test_app):
    mock_resolve.return_value = ("UCdelete_channel_test_1234", "Delete Channel")

    resp = test_app.post(
        "/api/channels",
        json={"url": "https://youtube.com/@delete"},
    )
    assert resp.status_code == 201
    channel_id = resp.json()["id"]

    resp = test_app.delete(f"/api/channels/{channel_id}")
    assert resp.status_code == 204

    resp = test_app.get("/api/channels")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_delete_channel_not_found(test_app):
    resp = test_app.delete("/api/channels/999")
    assert resp.status_code == 404


@patch("app.api.channels.resolve_channel_id")
def test_force_poll(mock_resolve, test_app):
    mock_resolve.return_value = ("UCpoll_channel_test_12345", "Poll Channel")

    resp = test_app.post(
        "/api/channels",
        json={"url": "https://youtube.com/@poll"},
    )
    assert resp.status_code == 201
    channel_id = resp.json()["id"]

    with patch("app.services.pipeline.process_channel"):
        resp = test_app.post(f"/api/channels/{channel_id}/poll")
    assert resp.status_code == 202
    assert resp.json()["detail"] == "Poll started"


def test_force_poll_not_found(test_app):
    resp = test_app.post("/api/channels/999/poll")
    assert resp.status_code == 404


@patch("app.api.channels.resolve_channel_id")
def test_list_channels_after_add(mock_resolve, test_app):
    mock_resolve.return_value = ("UClist_channel_test_123456", "Listed Channel")

    resp = test_app.post(
        "/api/channels",
        json={"url": "https://youtube.com/@listed"},
    )
    assert resp.status_code == 201

    resp = test_app.get("/api/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Listed Channel"
