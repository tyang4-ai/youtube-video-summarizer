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
