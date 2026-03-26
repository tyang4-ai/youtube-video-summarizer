import api from './client.ts';
import type { SummaryListItem, SummaryDetail } from '../types.ts';

export async function getSummaries(channelId?: number): Promise<SummaryListItem[]> {
  const params = channelId != null ? { channel_id: channelId } : {};
  const res = await api.get<SummaryListItem[]>('/summaries', { params });
  return res.data;
}

export async function getSummary(id: number): Promise<SummaryDetail> {
  const res = await api.get<SummaryDetail>(`/summaries/${id}`);
  return res.data;
}

export function downloadPdf(id: number): void {
  window.open(`/api/summaries/${id}/pdf`, '_blank');
}

export async function resendEmail(id: number): Promise<void> {
  await api.post(`/summaries/${id}/resend`);
}

export async function regenerateSummary(id: number): Promise<void> {
  await api.post(`/summaries/${id}/regenerate`);
}
