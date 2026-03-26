export interface Channel {
  id: number;
  youtube_channel_id: string;
  name: string;
  url: string;
  poll_interval_minutes: number;
  is_active: boolean;
  last_polled_at: string | null;
  created_at: string;
}

export interface SummaryListItem {
  id: number;
  video_id: number;
  video_title: string;
  channel_name: string;
  summary_text: string;
  email_sent: boolean;
  created_at: string;
}

export interface SummaryDetail {
  id: number;
  video_id: number;
  summary_text: string;
  timestamps: { timestamp: string; title: string; description: string }[];
  pdf_path: string | null;
  email_sent: boolean;
  created_at: string;
}

export interface EmailConfig {
  id: number;
  resend_api_key: string;
  sender_email: string;
  recipients: string[];
  is_active: boolean;
}

export interface LLMConfig {
  id: number;
  provider_type: string;
  api_key: string;
  base_url: string;
  model_name: string;
  system_prompt: string;
}

export interface DashboardData {
  channel_count: number;
  videos_processed: number;
  emails_sent: number;
  channels: DashboardChannel[];
}

export interface DashboardChannel {
  id: number;
  name: string;
  is_active: boolean;
  last_polled_at: string | null;
  videos: DashboardVideo[];
}

export interface DashboardVideo {
  id: number;
  title: string;
  status: string;
  published_at: string | null;
}
