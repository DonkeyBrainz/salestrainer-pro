import type { UserStatsResponse } from '@/types/stats';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function fetchUserStats(accessToken: string): Promise<UserStatsResponse> {
  const response = await fetch(`${API_BASE}/api/v1/users/me/stats`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: 'Failed to fetch stats' } }));
    throw new Error(error.error?.message || 'Failed to fetch stats');
  }

  return response.json() as Promise<UserStatsResponse>;
}
