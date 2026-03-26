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
