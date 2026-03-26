import api from './client';
import type { LLMConfig } from '../types';

export async function getLLMConfig(): Promise<LLMConfig> {
  const res = await api.get<LLMConfig>('/llm');
  return res.data;
}

export async function updateLLMConfig(data: Omit<LLMConfig, 'id'>): Promise<void> {
  await api.put('/llm', data);
}
