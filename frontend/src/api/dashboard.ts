import api from './client.ts';
import type { DashboardData, ActivityItem } from '../types.ts';

export async function getDashboard(): Promise<DashboardData> {
  const res = await api.get<DashboardData>('/dashboard');
  return res.data;
}

export async function getActivity(): Promise<ActivityItem[]> {
  const res = await api.get<ActivityItem[]>('/activity');
  return res.data;
}
