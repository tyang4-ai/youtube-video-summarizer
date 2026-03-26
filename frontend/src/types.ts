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
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  sender_email: string;
  recipients: string[];
  is_active: boolean;
}

export interface DashboardData {
  channel_count: number;
  videos_processed: number;
  emails_sent: number;
  next_poll_time: string | null;
}

export interface ActivityItem {
  id: number;
  action: string;
  status: string;
  error_message: string | null;
  video_title: string | null;
  channel_name: string | null;
  created_at: string;
}
