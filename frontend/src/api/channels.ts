import api from './client.ts';
import type { Channel } from '../types.ts';

export async function getChannels(): Promise<Channel[]> {
  const res = await api.get<Channel[]>('/channels');
  return res.data;
}

export async function addChannel(url: string, pollInterval: number): Promise<Channel> {
  const res = await api.post<Channel>('/channels', {
    url,
    poll_interval_minutes: pollInterval,
  });
  return res.data;
}

export async function updateChannel(
  id: number,
  data: { poll_interval_minutes?: number; is_active?: boolean },
): Promise<Channel> {
  const res = await api.put<Channel>(`/channels/${id}`, data);
  return res.data;
}

export async function deleteChannel(id: number): Promise<void> {
  await api.delete(`/channels/${id}`);
}

export async function pollChannel(id: number): Promise<void> {
  await api.post(`/channels/${id}/poll`);
}
