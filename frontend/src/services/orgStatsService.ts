import type {
  NationalStatsResponse,
  RegionStatsResponse,
  StoreStatsResponse,
} from '@/types/orgStats';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function getJson<T>(path: string, accessToken: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: 'Request failed' } }));
    throw new Error(error.error?.message || 'Request failed');
  }

  return response.json() as Promise<T>;
}

export function fetchStoreStats(storeId: string, accessToken: string): Promise<StoreStatsResponse> {
  return getJson<StoreStatsResponse>(`/api/v1/stores/${encodeURIComponent(storeId)}/stats`, accessToken);
}

export function fetchRegionStats(region: string, accessToken: string): Promise<RegionStatsResponse> {
  return getJson<RegionStatsResponse>(`/api/v1/regions/${encodeURIComponent(region)}/stats`, accessToken);
}

export function fetchNationalStats(accessToken: string): Promise<NationalStatsResponse> {
  return getJson<NationalStatsResponse>('/api/v1/organization/stats', accessToken);
}
