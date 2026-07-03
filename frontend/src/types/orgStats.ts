export interface AgentLeaderboardEntry {
  user_id: string;
  name: string;
  store_id: string | null;
  store_name: string | null;
  total_sessions: number;
  avg_score: number | null;
  current_streak: number;
}

export interface OrgRollup {
  total_sessions: number;
  avg_score: number | null;
  active_agent_count: number;
}

export interface StoreStatsResponse {
  store_id: string;
  store_name: string;
  region: string;
  rollup: OrgRollup;
  leaderboard: AgentLeaderboardEntry[];
}

export interface StoreSummary {
  store_id: string;
  store_name: string;
  rollup: OrgRollup;
}

export interface RegionStatsResponse {
  region: string;
  rollup: OrgRollup;
  stores: StoreSummary[];
  leaderboard: AgentLeaderboardEntry[];
}

export interface RegionSummary {
  region: string;
  rollup: OrgRollup;
  stores: StoreSummary[];
}

export interface NationalStatsResponse {
  rollup: OrgRollup;
  regions: RegionSummary[];
  leaderboard: AgentLeaderboardEntry[];
}
