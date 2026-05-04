export interface COREStageStats {
  stage: 'CONNECT' | 'OBSERVE' | 'RECOMMEND' | 'EXECUTE';
  mastery_pct: number;
  delta: number | null;
}

export interface RecentSessionActivity {
  session_id: string;
  persona_name: string | null;
  started_at: string; // ISO datetime string
  score: number | null;
  grade: string | null;
}

export interface UserStatsResponse {
  current_streak: number;
  longest_streak: number;
  sessions_this_week: number;
  weekly_goal: number;
  avg_score_this_week: number | null;
  core_mastery: COREStageStats[];
  recent_activity: RecentSessionActivity[];
  total_sessions: number;
}
