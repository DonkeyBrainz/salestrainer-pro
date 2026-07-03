import React, { useEffect, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { fetchStoreStats } from '@/services/orgStatsService';
import { AT } from '@/styles/tokens';
import {
  Avatar,
  CoreMini,
  DashChrome,
  SectionLabel,
  Sparkline,
  StatCard,
  formatLastActive,
  getEnabledRoles,
  scoreColor,
} from '@/components/dashboard/DashboardChrome';
import type { AgentLeaderboardEntry, StoreStatsResponse } from '@/types/orgStats';

const ADMIN_EMAILS = ['user@example.com'];

function initials(name: string): string {
  return name.trim()[0]?.toUpperCase() ?? '?';
}

export default function ManagerDashboardPage() {
  const { user, getValidToken } = useAuth();
  const [data, setData] = useState<StoreStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const storeId = user?.storeId ?? null;
  const isAdmin = !!user && ADMIN_EMAILS.some((e) => e.toLowerCase() === user.email?.toLowerCase());
  const enabledRoles = getEnabledRoles(user, isAdmin);

  useEffect(() => {
    if (!storeId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const token = await getValidToken();
        if (!token) {
          setError('Not authenticated');
          return;
        }
        const result = await fetchStoreStats(storeId, token);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load stats');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [storeId, getValidToken]);

  if (!storeId) {
    return (
      <DashChrome role="Manager" enabledRoles={enabledRoles} personName={user?.name ?? ''} personInit={initials(user?.name ?? '?')}>
        <EmptyState message="Your account isn't assigned to a store yet." />
      </DashChrome>
    );
  }

  if (loading) {
    return (
      <DashChrome role="Manager" enabledRoles={enabledRoles} personName={user?.name ?? ''} personInit={initials(user?.name ?? '?')}>
        <LoadingState />
      </DashChrome>
    );
  }

  if (error || !data) {
    return (
      <DashChrome role="Manager" enabledRoles={enabledRoles} personName={user?.name ?? ''} personInit={initials(user?.name ?? '?')}>
        <EmptyState message={error ?? 'Failed to load stats'} />
      </DashChrome>
    );
  }

  const sorted = data.leaderboard; // already sorted by the API
  const atRisk = sorted.filter((a) => a.flag);
  const brightSpot = [...sorted]
    .filter((a) => a.weekly_delta !== null)
    .sort((a, b) => (b.weekly_delta ?? 0) - (a.weekly_delta ?? 0))[0];

  return (
    <DashChrome
      role="Manager"
      enabledRoles={enabledRoles}
      crumb={`${data.store_name} · ${data.region}`}
      personName={user?.name ?? ''}
      personInit={initials(user?.name ?? '?')}
    >
      <div style={{ padding: '28px 36px 48px' }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontFamily: AT.display, fontSize: 32, fontWeight: 600, letterSpacing: '-0.02em' }}>
            {data.store_name} team <span style={{ color: AT.terra, fontStyle: 'italic' }}>overview</span>
          </div>
          <div style={{ marginTop: 6, fontSize: 13.5, color: AT.inkSoft }}>
            {sorted.length} agent{sorted.length !== 1 ? 's' : ''} · last updated today
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
          <StatCard
            label="Team avg score"
            value={data.rollup.avg_score ?? '—'}
            unit={data.rollup.avg_score !== null ? '/ 100' : undefined}
            accent={data.rollup.avg_score !== null ? scoreColor(data.rollup.avg_score) : AT.inkMuted}
            delta={
              data.rollup.avg_score_delta !== null
                ? `${data.rollup.avg_score_delta >= 0 ? '+' : ''}${data.rollup.avg_score_delta} ${data.rollup.avg_score_delta >= 0 ? '▲' : '▼'}`
                : undefined
            }
            deltaGood={data.rollup.avg_score_delta !== null && data.rollup.avg_score_delta >= 0}
            foot="This week's average across the team"
          />
          <StatCard
            label="Sessions this week"
            value={data.rollup.sessions_this_week}
            unit="total"
            accent={AT.sage}
            foot={`Across all ${sorted.length} agents`}
          />
          <StatCard
            label="Agents at risk"
            value={atRisk.length}
            unit="flagged"
            accent={AT.terra}
            foot="Declining trend, low activity, or low score"
          />
          <StatCard
            label="Store rank"
            value={data.store_rank ?? '—'}
            unit={`of ${data.store_count} stores`}
            accent={AT.butter}
            foot="Company-wide, by avg score"
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 16, alignItems: 'start' }}>
          <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: 22 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <SectionLabel>Team leaderboard</SectionLabel>
              <div style={{ fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted, letterSpacing: '0.14em', textTransform: 'uppercase' }}>
                Ranked by score
              </div>
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '24px 34px 1.3fr 70px 60px 70px 70px 20px',
                gap: 12,
                alignItems: 'center',
                padding: '0 2px 8px',
                fontFamily: AT.mono,
                fontSize: 9.5,
                color: AT.inkMuted,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                borderBottom: `1px solid ${AT.hair}`,
              }}
            >
              <div>#</div>
              <div />
              <div>Agent</div>
              <div>C·O·R·E</div>
              <div>Score</div>
              <div>Trend</div>
              <div>Sessions</div>
              <div />
            </div>
            {sorted.length === 0 ? (
              <div style={{ padding: '24px 2px', color: AT.inkMuted, fontSize: 13 }}>No agents assigned to this store yet.</div>
            ) : (
              sorted.map((a, i) => <LeaderboardRow key={a.user_id} entry={a} rank={i + 1} isLast={i === sorted.length - 1} />)
            )}
          </div>

          <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: 22 }}>
            <SectionLabel>Flagged agents</SectionLabel>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 16 }}>
              {atRisk.length === 0 && (
                <div style={{ fontSize: 12.5, color: AT.inkMuted }}>No agents currently flagged.</div>
              )}
              {atRisk.map((a) => (
                <div
                  key={a.user_id}
                  style={{ padding: '14px 16px', borderRadius: 10, background: AT.terraDim + '22', border: `1px solid ${AT.terraDim}` }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <Avatar initial={initials(a.name)} color={AT.terra} />
                    <div>
                      <div style={{ fontFamily: AT.display, fontSize: 15, fontWeight: 600 }}>{a.name}</div>
                      <div style={{ fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted }}>
                        Score {a.avg_score ?? '—'}
                        {a.weekly_delta !== null && ` · ${a.weekly_delta >= 0 ? '+' : ''}${a.weekly_delta} this week`}
                      </div>
                    </div>
                  </div>
                  <div style={{ fontSize: 12.5, color: AT.inkSoft, lineHeight: 1.5 }}>{a.flag}</div>
                </div>
              ))}
            </div>

            {brightSpot && brightSpot.weekly_delta !== null && brightSpot.weekly_delta > 0 && (
              <div
                style={{
                  marginTop: 22,
                  padding: '12px 14px',
                  borderRadius: 10,
                  background: 'rgba(155,208,124,0.08)',
                  border: `1px solid ${AT.sageDim}`,
                  fontSize: 12.5,
                  color: AT.inkSoft,
                  lineHeight: 1.5,
                }}
              >
                <span style={{ color: AT.sage, marginRight: 6 }}>✦</span>
                <b style={{ color: AT.ink }}>Bright spot:</b> {brightSpot.name}'s score is up {brightSpot.weekly_delta} pts this week — best gain on the team.
              </div>
            )}
          </div>
        </div>
      </div>
    </DashChrome>
  );
}

function LeaderboardRow({ entry, rank, isLast }: { entry: AgentLeaderboardEntry; rank: number; isLast: boolean }) {
  const color = entry.avg_score !== null ? scoreColor(entry.avg_score) : AT.inkMuted;
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '24px 34px 1.3fr 70px 60px 70px 70px 20px',
        gap: 12,
        alignItems: 'center',
        padding: '13px 2px',
        borderBottom: isLast ? 'none' : `1px solid ${AT.hairSoft}`,
      }}
    >
      <div style={{ fontFamily: AT.mono, fontSize: 12, color: AT.inkMuted }}>{rank}</div>
      <Avatar initial={initials(entry.name)} color={color} />
      <div>
        <div style={{ fontFamily: AT.display, fontSize: 15, fontWeight: 500 }}>{entry.name}</div>
        <div style={{ fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted, marginTop: 2 }}>
          Last active {formatLastActive(entry.last_active_at)}
        </div>
      </div>
      {entry.core ? (
        <CoreMini c={entry.core.connect} o={entry.core.observe} r={entry.core.recommend} e={entry.core.execute} />
      ) : (
        <div />
      )}
      <div style={{ fontFamily: AT.display, fontSize: 18, fontWeight: 700, color }}>{entry.avg_score ?? '—'}</div>
      {entry.score_trend.length >= 2 ? (
        <Sparkline points={entry.score_trend} color={(entry.weekly_delta ?? 0) >= 0 ? AT.sage : AT.terra} />
      ) : (
        <div />
      )}
      <div style={{ fontFamily: AT.mono, fontSize: 12, color: AT.inkSoft }}>{entry.total_sessions}</div>
      <div style={{ color: entry.flag ? AT.terra : AT.hair, fontSize: 14 }}>{entry.flag ? '●' : '·'}</div>
    </div>
  );
}

function LoadingState() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 64 }}>
      <div style={{ width: 32, height: 32, border: `2px solid ${AT.hair}`, borderTopColor: AT.terra, borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 64, gap: 12 }}>
      <AlertCircle style={{ width: 40, height: 40, color: AT.terra }} />
      <div style={{ color: AT.inkSoft, fontSize: 14 }}>{message}</div>
    </div>
  );
}
