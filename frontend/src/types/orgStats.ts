export interface CoreBreakdown {
  connect: number;
  observe: number;
  recommend: number;
  execute: number;
}

export interface AgentLeaderboardEntry {
  user_id: string;
  name: string;
  store_id: string | null;
  store_name: string | null;
  total_sessions: number;
  sessions_this_week: number;
  avg_score: number | null;
  current_streak: number;
  core: CoreBreakdown | null;
  score_trend: number[];
  weekly_delta: number | null;
  last_active_at: string | null;
  flag: string | null;
}

export interface OrgRollup {
  total_sessions: number;
  sessions_this_week: number;
  avg_score: number | null;
  avg_score_delta: number | null;
  active_agent_count: number;
}

export interface StoreStatsResponse {
  store_id: string;
  store_name: string;
  region: string;
  manager_name: string | null;
  rollup: OrgRollup;
  leaderboard: AgentLeaderboardEntry[];
  store_rank: number | null;
  store_count: number;
}

export interface StoreSummary {
  store_id: string;
  store_name: string;
  manager_name: string | null;
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
