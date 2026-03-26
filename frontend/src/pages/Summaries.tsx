import { useEffect, useState } from 'react';
import type { SummaryListItem, SummaryDetail, Channel } from '../types.ts';
import {
  getSummaries,
  getSummary,
  downloadPdf,
  resendEmail,
  regenerateSummary,
} from '../api/summaries.ts';
import { getChannels } from '../api/channels.ts';
import StatusBadge from '../components/StatusBadge.tsx';

export default function Summaries() {
  const [summaries, setSummaries] = useState<SummaryListItem[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<number | undefined>(undefined);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<SummaryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  async function loadSummaries(channelId?: number) {
    try {
      setError('');
      setLoading(true);
      const data = await getSummaries(channelId);
      setSummaries(data);
    } catch {
      setError('Failed to load summaries');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
      try {
        const chs = await getChannels();
        setChannels(chs);
      } catch {
        // non-critical
      }
      await loadSummaries();
    }
    init();
  }, []);

  function handleFilterChange(value: string) {
    const channelId = value === '' ? undefined : Number(value);
    setSelectedChannel(channelId);
    setExpandedId(null);
    setDetail(null);
    loadSummaries(channelId);
  }

  async function handleExpand(id: number) {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    try {
      const d = await getSummary(id);
      setDetail(d);
      setExpandedId(id);
    } catch {
      setError('Failed to load summary details');
    }
  }

  async function handleResend(id: number) {
    try {
      setActionMsg('');
      await resendEmail(id);
      setActionMsg('Email resend triggered.');
    } catch {
      setActionMsg('Failed to resend email.');
    }
  }

  async function handleRegenerate(id: number) {
    try {
      setActionMsg('');
      await regenerateSummary(id);
      setActionMsg('Regeneration triggered.');
    } catch {
      setActionMsg('Failed to regenerate summary.');
    }
  }

  if (loading && summaries.length === 0)
    return <div className="loading">Loading...</div>;

  return (
    <div>
      <h1>Summaries</h1>

      {error && <div className="alert alert-error">{error}</div>}
      {actionMsg && <div className="alert alert-success">{actionMsg}</div>}

      <div className="filter-bar">
        <div className="form-group">
          <label htmlFor="channel-filter">Filter by Channel</label>
          <select
            id="channel-filter"
            value={selectedChannel ?? ''}
            onChange={(e) => handleFilterChange(e.target.value)}
          >
            <option value="">All Channels</option>
            {channels.map((ch) => (
              <option key={ch.id} value={ch.id}>
                {ch.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {summaries.length === 0 ? (
        <p className="empty-state">No summaries yet.</p>
      ) : (
        <div className="summary-list">
          {summaries.map((s) => (
            <div key={s.id} className="card">
              <div
                className="card-header"
                onClick={() => handleExpand(s.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter') handleExpand(s.id); }}
              >
                <div className="card-title">{s.video_title}</div>
                <div className="card-meta">
                  <span>{s.channel_name}</span>
                  <span>{new Date(s.created_at).toLocaleDateString()}</span>
                  <StatusBadge status={s.email_sent ? 'SENT' : 'PENDING'} />
                </div>
              </div>

              {expandedId === s.id && detail && (
                <div className="card-body">
                  <div className="summary-text">{detail.summary_text}</div>

                  {detail.timestamps.length > 0 && (
                    <div className="timestamps-list">
                      <h3>Timestamps</h3>
                      {detail.timestamps.map((ts, i) => (
                        <div key={i} className="timestamp-section">
                          <span className="ts-time">{ts.timestamp}</span>
                          <span className="ts-title">{ts.title}</span>
                          <p className="ts-desc">{ts.description}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="card-actions">
                    <button
                      className="btn btn-sm"
                      onClick={() => downloadPdf(s.id)}
                    >
                      Download PDF
                    </button>
                    <button
                      className="btn btn-sm"
                      onClick={() => handleResend(s.id)}
                    >
                      Re-send Email
                    </button>
                    <button
                      className="btn btn-sm"
                      onClick={() => handleRegenerate(s.id)}
                    >
                      Re-generate
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
