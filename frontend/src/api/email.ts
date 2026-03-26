import api from './client.ts';
import type { EmailConfig } from '../types.ts';

export async function getEmailConfig(): Promise<EmailConfig | null> {
  const res = await api.get<EmailConfig | null>('/email');
  return res.data;
}

export async function updateEmailConfig(data: EmailConfig): Promise<void> {
  await api.put('/email', data);
}

export async function sendTestEmail(): Promise<void> {
  await api.post('/email/test');
}
