import { useEffect, useState } from 'react';
import type { Channel } from '../types.ts';
import {
  getChannels,
  addChannel,
  updateChannel,
  deleteChannel,
  pollChannel,
} from '../api/channels.ts';
import StatusBadge from '../components/StatusBadge.tsx';

export default function Channels() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [url, setUrl] = useState('');
  const [interval, setInterval] = useState(30);
  const [adding, setAdding] = useState(false);

  async function load() {
    try {
      setError('');
      const data = await getChannels();
      setChannels(data);
    } catch {
      setError('Failed to load channels');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setAdding(true);
    setError('');
    try {
      const ch = await addChannel(url.trim(), interval);
      setChannels((prev) => [...prev, ch]);
      setUrl('');
    } catch {
      setError('Failed to add channel. Check the URL and try again.');
    } finally {
      setAdding(false);
    }
  }

  async function handleToggle(ch: Channel) {
    try {
      const updated = await updateChannel(ch.id, { is_active: !ch.is_active });
      setChannels((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch {
      setError('Failed to update channel');
    }
  }

  async function handleCheckNow(id: number) {
    try {
      await pollChannel(id);
      setError('');
    } catch {
      setError('Failed to trigger poll');
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm('Are you sure you want to delete this channel?')) return;
    try {
      await deleteChannel(id);
      setChannels((prev) => prev.filter((c) => c.id !== id));
    } catch {
      setError('Failed to delete channel');
    }
  }

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div>
      <h1>Channels</h1>

      {error && <div className="alert alert-error">{error}</div>}

      <form className="add-form" onSubmit={handleAdd}>
        <div className="form-group">
          <label htmlFor="channel-url">YouTube Channel URL</label>
          <input
            id="channel-url"
            type="text"
            placeholder="https://youtube.com/@channel"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="poll-interval">Poll Interval</label>
          <select
            id="poll-interval"
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value))}
          >
            <option value={15}>15 minutes</option>
            <option value={30}>30 minutes</option>
            <option value={60}>1 hour</option>
            <option value={360}>6 hours</option>
          </select>
        </div>
        <button type="submit" className="btn btn-primary" disabled={adding}>
          {adding ? 'Adding...' : 'Add Channel'}
        </button>
      </form>

      {channels.length === 0 ? (
        <p className="empty-state">No channels added yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>URL</th>
              <th>Interval</th>
              <th>Status</th>
              <th>Last Checked</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {channels.map((ch) => (
              <tr key={ch.id}>
                <td>{ch.name}</td>
                <td>
                  <a href={ch.url} target="_blank" rel="noopener noreferrer">
                    {ch.url.length > 40 ? ch.url.slice(0, 40) + '...' : ch.url}
                  </a>
                </td>
                <td>{ch.poll_interval_minutes}m</td>
                <td>
                  <StatusBadge status={ch.is_active ? 'active' : 'paused'} />
                </td>
                <td>{ch.last_polled_at ? new Date(ch.last_polled_at).toLocaleString() : 'Never'}</td>
                <td className="actions-cell">
                  <button
                    className="btn btn-sm"
                    onClick={() => handleToggle(ch)}
                  >
                    {ch.is_active ? 'Pause' : 'Resume'}
                  </button>
                  <button
                    className="btn btn-sm"
                    onClick={() => handleCheckNow(ch.id)}
                  >
                    Check Now
                  </button>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDelete(ch.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
