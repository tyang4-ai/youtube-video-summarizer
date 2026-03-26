import { useEffect, useState } from 'react';
import type { DashboardData, ActivityItem } from '../types.ts';
import { getDashboard, getActivity } from '../api/dashboard.ts';
import StatsCard from '../components/StatsCard.tsx';
import StatusBadge from '../components/StatusBadge.tsx';

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

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardData | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [dashData, actData] = await Promise.all([getDashboard(), getActivity()]);
        setStats(dashData);
        setActivity(actData);
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
        <StatsCard label="Channels" value={stats?.channel_count ?? 0} />
        <StatsCard label="Videos Processed" value={stats?.videos_processed ?? 0} />
        <StatsCard label="Emails Sent" value={stats?.emails_sent ?? 0} />
        <StatsCard label="Next Poll" value={stats?.next_poll_time ?? 'N/A'} />
      </div>

      <h2>Recent Activity</h2>
      {activity.length === 0 ? (
        <p className="empty-state">No activity yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Video</th>
              <th>Channel</th>
              <th>Action</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {activity.map((item) => (
              <tr key={item.id}>
                <td><StatusBadge status={item.status} /></td>
                <td>{item.video_title ?? '-'}</td>
                <td>{item.channel_name ?? '-'}</td>
                <td>{item.action}</td>
                <td>{timeAgo(item.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
