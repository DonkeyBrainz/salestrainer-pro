import React, { useEffect, useState } from 'react';
import type { COREStageStats, RecentSessionActivity, UserStatsResponse } from '@/types/stats';

const CORE_COLORS: Record<string, string> = {
  CONNECT: '#5a7a6a',   // sage green
  OBSERVE: '#8B5E3C',   // terra
  RECOMMEND: '#b8993a', // butter
  EXECUTE: '#7a8a85',   // muted slate
};

const GRADE_COLORS: Record<string, string> = {
  A: '#5a7a6a',
  B: '#7a9a8a',
  C: '#b8993a',
  D: '#c87050',
  F: '#c87050',
};

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SkeletonBar() {
  return <div className="h-3 bg-stone-200 rounded animate-pulse" />;
}

function StatsDashboardSkeleton() {
  return (
    <div className="bg-white/80 backdrop-blur-md rounded-2xl border border-stone-200 p-6 space-y-5">
      <div className="grid grid-cols-2 gap-4">
        {[0, 1].map((i) => (
          <div key={i} className="bg-stone-50 rounded-xl p-4 space-y-2">
            <div className="h-2 w-16 bg-stone-200 rounded animate-pulse" />
            <div className="h-8 w-12 bg-stone-200 rounded animate-pulse" />
            <SkeletonBar />
          </div>
        ))}
      </div>
      <div className="space-y-3">
        <div className="h-2 w-24 bg-stone-200 rounded animate-pulse" />
        {[0, 1, 2, 3].map((i) => (
          <SkeletonBar key={i} />
        ))}
      </div>
    </div>
  );
}

// ── Streak dots ───────────────────────────────────────────────────────────────

function StreakDots({ sessionsThisWeek, weeklyGoal }: { sessionsThisWeek: number; weeklyGoal: number }) {
  return (
    <div className="flex gap-1 mt-2">
      {Array.from({ length: weeklyGoal }).map((_, i) => (
        <div
          key={i}
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: i < sessionsThisWeek ? '#5a7a6a' : '#e7e5e0' }}
        />
      ))}
    </div>
  );
}

// ── CORE skill bar ────────────────────────────────────────────────────────────

function SkillBar({ stage }: { stage: COREStageStats }) {
  const letter = stage.stage[0];
  const color = CORE_COLORS[stage.stage] || '#7a8a85';
  const deltaPositive = stage.delta !== null && stage.delta > 0;
  const deltaNegative = stage.delta !== null && stage.delta < 0;

  return (
    <div className="flex items-center gap-3">
      <span
        className="w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
        style={{ backgroundColor: color }}
      >
        {letter}
      </span>
      <div className="flex-1">
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-stone-500 capitalize">{stage.stage.toLowerCase()}</span>
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-[#2C2825]">{Math.round(stage.mastery_pct)}%</span>
            {stage.delta !== null && (
              <span
                className="text-[10px] font-mono"
                style={{ color: deltaPositive ? '#5a7a6a' : deltaNegative ? '#c87050' : '#9a9590' }}
              >
                {deltaPositive ? '+' : ''}{stage.delta.toFixed(0)}
              </span>
            )}
          </div>
        </div>
        <div className="h-1.5 bg-stone-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${stage.mastery_pct}%`, backgroundColor: color }}
          />
        </div>
      </div>
    </div>
  );
}

// ── Recent activity row ───────────────────────────────────────────────────────

function ActivityRow({ session }: { session: RecentSessionActivity }) {
  const gradeColor = session.grade ? GRADE_COLORS[session.grade] ?? '#9a9590' : '#9a9590';
  return (
    <div className="flex items-center justify-between py-1.5">
      <div>
        <p className="text-sm font-medium text-[#2C2825]">{session.persona_name ?? 'Session'}</p>
        <p className="text-[11px] text-stone-400 font-mono">{formatRelativeTime(session.started_at)}</p>
      </div>
      <div className="flex items-center gap-2">
        <span
          className="text-sm font-bold"
          style={{ color: gradeColor }}
        >
          {session.score ?? '—'}
        </span>
        {session.grade && (
          <span
            className="text-[10px] font-bold px-1.5 py-0.5 rounded uppercase"
            style={{ backgroundColor: `${gradeColor}20`, color: gradeColor }}
          >
            {session.grade}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  accessToken: string;
}

export default function UserStatsDashboard({ accessToken }: Props) {
  const [stats, setStats] = useState<UserStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    import('@/services/statsService').then(({ fetchUserStats }) => {
      fetchUserStats(accessToken)
        .then((data) => { if (!cancelled) { setStats(data); setLoading(false); } })
        .catch(() => { if (!cancelled) setLoading(false); });
    });
    return () => { cancelled = true; };
  }, [accessToken]);

  if (loading) return <StatsDashboardSkeleton />;
  if (!stats || stats.total_sessions === 0) return null;

  const sessionsLeft = Math.max(0, stats.weekly_goal - stats.sessions_this_week);
  const weeklyFoot = sessionsLeft === 0
    ? `Goal hit! Avg score ${stats.avg_score_this_week ?? '—'}.`
    : `${sessionsLeft} to go${stats.avg_score_this_week != null ? `. Avg score ${stats.avg_score_this_week}.` : '.'}`;

  return (
    <div className="bg-white/80 backdrop-blur-md rounded-2xl border border-stone-200 shadow-sm p-6 space-y-5 animate-fade-in">
      {/* Stat cards row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Streak */}
        <div className="bg-stone-50 rounded-xl p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 mb-1">Streak</p>
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-serif-display text-[#2C2825]">{stats.current_streak}</span>
            <span className="text-sm text-stone-400">days</span>
          </div>
          <StreakDots sessionsThisWeek={stats.sessions_this_week} weeklyGoal={stats.weekly_goal} />
          {stats.longest_streak > 0 && (
            <p className="text-[11px] text-stone-400 mt-2">
              Best: {stats.longest_streak} day{stats.longest_streak !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        {/* This week */}
        <div className="bg-stone-50 rounded-xl p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 mb-1">This week</p>
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-serif-display text-[#2C2825]">{stats.sessions_this_week}</span>
            <span className="text-sm text-stone-400">/ {stats.weekly_goal}</span>
          </div>
          <div className="flex gap-0.5 mt-2">
            {Array.from({ length: stats.weekly_goal }).map((_, i) => (
              <div
                key={i}
                className="flex-1 rounded-sm"
                style={{
                  height: 12,
                  backgroundColor: i < stats.sessions_this_week ? '#8B5E3C' : '#e7e5e0',
                }}
              />
            ))}
          </div>
          <p className="text-[11px] text-stone-400 mt-2">{weeklyFoot}</p>
        </div>
      </div>

      {/* CORE mastery */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 mb-3">
          C.O.R.E. Mastery
        </p>
        <div className="space-y-3">
          {stats.core_mastery.map((stage) => (
            <SkillBar key={stage.stage} stage={stage} />
          ))}
        </div>
      </div>

      {/* Recent activity */}
      {stats.recent_activity.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 mb-1">
            Recent activity
          </p>
          <div className="divide-y divide-stone-100">
            {stats.recent_activity.map((session) => (
              <ActivityRow key={session.session_id} session={session} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
