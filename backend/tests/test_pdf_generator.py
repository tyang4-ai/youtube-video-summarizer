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
