import { useEffect, useState } from 'react';
import type { EmailConfig, LLMConfig } from '../types';
import { getEmailConfig, updateEmailConfig, sendTestEmail } from '../api/email';
import { getLLMConfig, updateLLMConfig } from '../api/llm';

const defaultEmailConfig: EmailConfig = {
  id: 0,
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  sender_email: '',
  recipients: [],
  is_active: false,
};

const defaultLLMConfig: LLMConfig = {
  id: 0,
  provider_type: 'groq',
  api_key: '',
  base_url: 'https://api.groq.com/openai/v1',
  model_name: 'llama-3.3-70b-versatile',
  system_prompt: '',
};

export default function Settings() {
  // LLM state
  const [llmConfig, setLlmConfig] = useState<LLMConfig>(defaultLLMConfig);
  const [llmLoading, setLlmLoading] = useState(true);
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmMessage, setLlmMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Email state
  const [emailConfig, setEmailConfig] = useState<EmailConfig>(defaultEmailConfig);
  const [newRecipient, setNewRecipient] = useState('');
  const [emailLoading, setEmailLoading] = useState(true);
  const [emailSaving, setEmailSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [emailMessage, setEmailMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Load LLM config
  useEffect(() => {
    async function load() {
      try {
        const data = await getLLMConfig();
        if (data) setLlmConfig(data);
      } catch {
        setLlmMessage({ type: 'error', text: 'Failed to load LLM settings' });
      } finally {
        setLlmLoading(false);
      }
    }
    load();
  }, []);

  // Load Email config
  useEffect(() => {
    async function load() {
      try {
        const data = await getEmailConfig();
        if (data) setEmailConfig(data);
      } catch {
        setEmailMessage({ type: 'error', text: 'Failed to load email settings' });
      } finally {
        setEmailLoading(false);
      }
    }
    load();
  }, []);

  // LLM handlers
  function handleLLMChange(field: keyof LLMConfig, value: string) {
    setLlmConfig((prev) => ({ ...prev, [field]: value }));
  }

  async function handleLLMSave(e: React.FormEvent) {
    e.preventDefault();
    setLlmSaving(true);
    setLlmMessage(null);
    try {
      const { id: _, ...data } = llmConfig;
      await updateLLMConfig(data);
      setLlmMessage({ type: 'success', text: 'LLM settings saved successfully' });
    } catch {
      setLlmMessage({ type: 'error', text: 'Failed to save LLM settings' });
    } finally {
      setLlmSaving(false);
    }
  }

  // Email handlers
  function handleEmailChange(field: keyof EmailConfig, value: string | number | boolean) {
    setEmailConfig((prev) => ({ ...prev, [field]: value }));
  }

  function handleAddRecipient() {
    const email = newRecipient.trim();
    if (!email) return;
    if (emailConfig.recipients.includes(email)) return;
    setEmailConfig((prev) => ({ ...prev, recipients: [...prev.recipients, email] }));
    setNewRecipient('');
  }

  function handleRemoveRecipient(email: string) {
    setEmailConfig((prev) => ({
      ...prev,
      recipients: prev.recipients.filter((r) => r !== email),
    }));
  }

  async function handleEmailSave(e: React.FormEvent) {
    e.preventDefault();
    setEmailSaving(true);
    setEmailMessage(null);
    try {
      await updateEmailConfig(emailConfig);
      setEmailMessage({ type: 'success', text: 'Email settings saved successfully' });
    } catch {
      setEmailMessage({ type: 'error', text: 'Failed to save email settings' });
    } finally {
      setEmailSaving(false);
    }
  }

  async function handleTestEmail() {
    setTesting(true);
    setEmailMessage(null);
    try {
      await sendTestEmail();
      setEmailMessage({ type: 'success', text: 'Test email sent successfully!' });
    } catch {
      setEmailMessage({ type: 'error', text: 'Test email failed. Check your settings.' });
    } finally {
      setTesting(false);
    }
  }

  if (llmLoading || emailLoading) return <div className="loading">Loading...</div>;

  return (
    <div>
      <h1>Settings</h1>

      {/* LLM Settings Section */}
      <div className="settings-section">
        <h2>LLM Settings</h2>

        {llmMessage && (
          <div className={`alert alert-${llmMessage.type}`}>{llmMessage.text}</div>
        )}

        <form onSubmit={handleLLMSave}>
          <div className="form-group">
            <label htmlFor="llm-provider">Provider</label>
            <select
              id="llm-provider"
              value={llmConfig.provider_type}
              onChange={(e) => {
                const provider = e.target.value;
                setLlmConfig((prev) => ({
                  ...prev,
                  provider_type: provider,
                  base_url: provider === 'groq' ? 'https://api.groq.com/openai/v1' : '',
                  model_name: provider === 'groq' ? 'llama-3.3-70b-versatile' : 'claude-sonnet-4-20250514',
                }));
              }}
            >
              <option value="groq">Groq (Llama)</option>
              <option value="claude">Claude (Anthropic)</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="llm-api-key">API Key</label>
            <input
              id="llm-api-key"
              type="password"
              value={llmConfig.api_key}
              onChange={(e) => handleLLMChange('api_key', e.target.value)}
              placeholder={llmConfig.provider_type === 'claude' ? 'sk-ant-...' : 'gsk_...'}
            />
          </div>

          {llmConfig.provider_type === 'groq' && (
            <div className="form-group">
              <label htmlFor="llm-base-url">Base URL</label>
              <input
                id="llm-base-url"
                type="text"
                value={llmConfig.base_url}
                onChange={(e) => handleLLMChange('base_url', e.target.value)}
                placeholder="https://api.groq.com/openai/v1"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="llm-model-name">Model Name</label>
            <input
              id="llm-model-name"
              type="text"
              value={llmConfig.model_name}
              onChange={(e) => handleLLMChange('model_name', e.target.value)}
              placeholder={llmConfig.provider_type === 'claude' ? 'claude-sonnet-4-20250514' : 'llama-3.3-70b-versatile'}
            />
          </div>

          <div className="form-group">
            <label htmlFor="llm-system-prompt">System Prompt</label>
            <textarea
              id="llm-system-prompt"
              rows={8}
              value={llmConfig.system_prompt}
              onChange={(e) => handleLLMChange('system_prompt', e.target.value)}
              placeholder="Enter system prompt for the LLM..."
              style={{
                width: '100%',
                padding: '10px 12px',
                background: '#16162b',
                border: '1px solid #2d2d44',
                borderRadius: '6px',
                color: '#e0e0e0',
                fontSize: '14px',
                outline: 'none',
                resize: 'vertical',
                fontFamily: 'inherit',
              }}
            />
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={llmSaving}>
              {llmSaving ? 'Saving...' : 'Save LLM Settings'}
            </button>
          </div>
        </form>
      </div>

      {/* Email Settings Section */}
      <div className="settings-section">
        <h2>Email Settings</h2>

        {emailMessage && (
          <div className={`alert alert-${emailMessage.type}`}>{emailMessage.text}</div>
        )}

        <form onSubmit={handleEmailSave}>
          <div className="form-group">
            <label htmlFor="smtp-host">SMTP Host</label>
            <input
              id="smtp-host"
              type="text"
              value={emailConfig.smtp_host}
              onChange={(e) => handleEmailChange('smtp_host', e.target.value)}
              placeholder="smtp.gmail.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="smtp-port">SMTP Port</label>
            <input
              id="smtp-port"
              type="number"
              value={emailConfig.smtp_port}
              onChange={(e) => handleEmailChange('smtp_port', Number(e.target.value))}
            />
          </div>

          <div className="form-group">
            <label htmlFor="smtp-user">SMTP User</label>
            <input
              id="smtp-user"
              type="text"
              value={emailConfig.smtp_user}
              onChange={(e) => handleEmailChange('smtp_user', e.target.value)}
              placeholder="user@gmail.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="smtp-password">SMTP Password</label>
            <input
              id="smtp-password"
              type="password"
              value={emailConfig.smtp_password}
              onChange={(e) => handleEmailChange('smtp_password', e.target.value)}
              placeholder="App password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="sender-email">Sender Email</label>
            <input
              id="sender-email"
              type="email"
              value={emailConfig.sender_email}
              onChange={(e) => handleEmailChange('sender_email', e.target.value)}
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
              {emailConfig.recipients.map((r) => (
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
                checked={emailConfig.is_active}
                onChange={(e) => handleEmailChange('is_active', e.target.checked)}
              />
              <span>Email sending active</span>
            </label>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={emailSaving}>
              {emailSaving ? 'Saving...' : 'Save Email Settings'}
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
    </div>
  );
}
