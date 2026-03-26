import { useEffect, useState } from 'react';
import type { EmailConfig } from '../types.ts';
import { getEmailConfig, updateEmailConfig, sendTestEmail } from '../api/email.ts';

const defaultConfig: EmailConfig = {
  id: 0,
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  sender_email: '',
  recipients: [],
  is_active: false,
};

export default function EmailSettings() {
  const [config, setConfig] = useState<EmailConfig>(defaultConfig);
  const [newRecipient, setNewRecipient] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getEmailConfig();
        if (data) setConfig(data);
      } catch {
        setMessage({ type: 'error', text: 'Failed to load email settings' });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function handleChange(field: keyof EmailConfig, value: string | number | boolean) {
    setConfig((prev) => ({ ...prev, [field]: value }));
  }

  function handleAddRecipient() {
    const email = newRecipient.trim();
    if (!email) return;
    if (config.recipients.includes(email)) return;
    setConfig((prev) => ({ ...prev, recipients: [...prev.recipients, email] }));
    setNewRecipient('');
  }

  function handleRemoveRecipient(email: string) {
    setConfig((prev) => ({
      ...prev,
      recipients: prev.recipients.filter((r) => r !== email),
    }));
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await updateEmailConfig(config);
      setMessage({ type: 'success', text: 'Settings saved successfully' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  }

  async function handleTestEmail() {
    setTesting(true);
    setMessage(null);
    try {
      await sendTestEmail();
      setMessage({ type: 'success', text: 'Test email sent successfully!' });
    } catch {
      setMessage({ type: 'error', text: 'Test email failed. Check your settings.' });
    } finally {
      setTesting(false);
    }
  }

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div>
      <h1>Email Settings</h1>

      {message && (
        <div className={`alert alert-${message.type}`}>{message.text}</div>
      )}

      <form className="settings-form" onSubmit={handleSave}>
        <div className="form-group">
          <label htmlFor="smtp-host">SMTP Host</label>
          <input
            id="smtp-host"
            type="text"
            value={config.smtp_host}
            onChange={(e) => handleChange('smtp_host', e.target.value)}
            placeholder="smtp.gmail.com"
          />
        </div>

        <div className="form-group">
          <label htmlFor="smtp-port">SMTP Port</label>
          <input
            id="smtp-port"
            type="number"
            value={config.smtp_port}
            onChange={(e) => handleChange('smtp_port', Number(e.target.value))}
          />
        </div>

        <div className="form-group">
          <label htmlFor="smtp-user">SMTP User</label>
          <input
            id="smtp-user"
            type="text"
            value={config.smtp_user}
            onChange={(e) => handleChange('smtp_user', e.target.value)}
            placeholder="user@gmail.com"
          />
        </div>

        <div className="form-group">
          <label htmlFor="smtp-password">SMTP Password</label>
          <input
            id="smtp-password"
            type="password"
            value={config.smtp_password}
            onChange={(e) => handleChange('smtp_password', e.target.value)}
            placeholder="App password"
          />
        </div>

        <div className="form-group">
          <label htmlFor="sender-email">Sender Email</label>
          <input
            id="sender-email"
            type="email"
            value={config.sender_email}
            onChange={(e) => handleChange('sender_email', e.target.value)}
            placeholder="noreply@example.com"
          />
        </div>

        <div className="form-group">
          <label>Recipients</label>
          <div className="recipient-input-row">
            <input
              type="email"
              value={newRecipient}
              onChange={(e) => setNewRecipient(e.target.value)}
              placeholder="Add email address"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddRecipient();
                }
              }}
            />
            <button
              type="button"
              className="btn btn-sm"
              onClick={handleAddRecipient}
            >
              Add
            </button>
          </div>
          <ul className="recipient-list">
            {config.recipients.map((r) => (
              <li key={r} className="recipient-item">
                <span>{r}</span>
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  onClick={() => handleRemoveRecipient(r)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="form-group toggle-group">
          <label htmlFor="email-active">
            <input
              id="email-active"
              type="checkbox"
              checked={config.is_active}
              onChange={(e) => handleChange('is_active', e.target.checked)}
            />
            <span>Email sending active</span>
          </label>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          <button
            type="button"
            className="btn"
            onClick={handleTestEmail}
            disabled={testing}
          >
            {testing ? 'Sending...' : 'Send Test Email'}
          </button>
        </div>
      </form>
    </div>
  );
}
