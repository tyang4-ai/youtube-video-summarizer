import { useEffect, useState } from 'react';
import type { DashboardData } from '../types';
import { getDashboard } from '../api/dashboard';
import StatsCard from '../components/StatsCard';
import StatusBadge from '../components/StatusBadge';

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const seconds = Math.floor((now - then) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const dashData = await getDashboard();
        setData(dashData);
      } catch {
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="alert alert-error">{error}</div>;

  return (
    <div>
      <h1>Dashboard</h1>

      <div className="stats-row">
        <StatsCard label="Channels" value={data?.channel_count ?? 0} />
        <StatsCard label="Videos Processed" value={data?.videos_processed ?? 0} />
        <StatsCard label="Emails Sent" value={data?.emails_sent ?? 0} />
      </div>

      <h2>Monitored Channels</h2>

      {(!data?.channels || data.channels.length === 0) ? (
        <p className="empty-state">No channels added yet.</p>
      ) : (
        data.channels.map((channel) => (
          <div key={channel.id} className="channel-card">
            <div className="channel-card-header">
              <h3>{channel.name}</h3>
              <StatusBadge status={channel.is_active ? 'active' : 'paused'} />
            </div>
            <div className="channel-card-meta">
              Last checked: {channel.last_polled_at ? timeAgo(channel.last_polled_at) : 'Never'}
            </div>
            {channel.videos.length === 0 ? (
              <p className="empty-state" style={{ padding: '8px 0' }}>No videos yet.</p>
            ) : (
              channel.videos.map((video) => (
                <div key={video.id} className="video-list-item">
                  <StatusBadge status={video.status} />
                  <span className="video-title">{video.title}</span>
                  <span className="video-date">
                    {video.published_at ? formatDate(video.published_at) : ''}
                  </span>
                </div>
              ))
            )}
          </div>
        ))
      )}
    </div>
  );
}
