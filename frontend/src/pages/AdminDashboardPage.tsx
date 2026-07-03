import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { fetchNationalStats, fetchRegionStats } from '@/services/orgStatsService';
import { AT } from '@/styles/tokens';
import {
  Avatar,
  DashChrome,
  SectionLabel,
  StatCard,
  getEnabledRoles,
  scoreColor,
} from '@/components/dashboard/DashboardChrome';
import type { AgentLeaderboardEntry, RegionSummary, StoreSummary } from '@/types/orgStats';

const ADMIN_EMAILS = ['user@example.com'];

const REGION_NAMES: Record<string, string> = { NC: 'North Carolina', SC: 'South Carolina', TX: 'Texas' };

function initials(name: string): string {
  return name.trim()[0]?.toUpperCase() ?? '?';
}

interface StoreRow extends StoreSummary {
  region: string;
}

export default function AdminDashboardPage() {
  const { user, getValidToken } = useAuth();
  const isAdmin = !!user && ADMIN_EMAILS.some((e) => e.toLowerCase() === user.email?.toLowerCase());
  const scopeRegion = !isAdmin && user?.role === 'regional_director' ? user.region ?? null : null;

  const [regions, setRegions] = useState<RegionSummary[] | null>(null);
  const [leaderboard, setLeaderboard] = useState<AgentLeaderboardEntry[]>([]);
  const [crumb, setCrumb] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAdmin && !scopeRegion) {
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
        if (isAdmin) {
          const data = await fetchNationalStats(token);
          if (!cancelled) {
            setRegions(data.regions);
            setLeaderboard(data.leaderboard);
            setCrumb('All regions');
          }
        } else if (scopeRegion) {
          const data = await fetchRegionStats(scopeRegion, token);
          if (!cancelled) {
            setRegions([{ region: data.region, rollup: data.rollup, stores: data.stores }]);
            setLeaderboard(data.leaderboard);
            setCrumb(`${data.region} Region`);
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load stats');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAdmin, scopeRegion, getValidToken]);

  const allStores: StoreRow[] = useMemo(
    () => (regions ?? []).flatMap((r) => r.stores.map((s) => ({ ...s, region: r.region }))),
    [regions]
  );
  const totalAgents = useMemo(
    () => (regions ?? []).reduce((sum, r) => sum + r.rollup.active_agent_count, 0),
    [regions]
  );
  const orgAvg = useMemo(() => {
    const scored = allStores.map((s) => s.rollup.avg_score).filter((v): v is number => v !== null);
    if (scored.length === 0) return null;
    return Math.round(scored.reduce((a, b) => a + b, 0) / scored.length);
  }, [allStores]);
  const topRegion = useMemo(() => {
    const scored = (regions ?? []).filter((r) => r.rollup.avg_score !== null);
    if (scored.length === 0) return null;
    return [...scored].sort((a, b) => (b.rollup.avg_score ?? 0) - (a.rollup.avg_score ?? 0))[0];
  }, [regions]);
  const ranked = useMemo(
    () => [...allStores].sort((a, b) => (b.rollup.avg_score ?? -1) - (a.rollup.avg_score ?? -1)),
    [allStores]
  );
  const scoredLeaderboard = leaderboard.filter((e) => e.avg_score !== null);
  const topPerformers = scoredLeaderboard.slice(0, 5);
  const bottomPerformers = scoredLeaderboard.slice(-5).reverse();

  const personName = user?.name ?? '';
  const personInit = initials(personName || '?');
  const enabledRoles = getEnabledRoles(user, isAdmin);

  if (!isAdmin && !scopeRegion) {
    return (
      <DashChrome role="Admin" enabledRoles={enabledRoles} personName={personName} personInit={personInit}>
        <EmptyState message="This dashboard is for regional directors and admins." />
      </DashChrome>
    );
  }

  if (loading) {
    return (
      <DashChrome role="Admin" enabledRoles={enabledRoles} personName={personName} personInit={personInit}>
        <LoadingState />
      </DashChrome>
    );
  }

  if (error || !regions) {
    return (
      <DashChrome role="Admin" enabledRoles={enabledRoles} personName={personName} personInit={personInit}>
        <EmptyState message={error ?? 'Failed to load stats'} />
      </DashChrome>
    );
  }

  return (
    <DashChrome role="Admin" enabledRoles={enabledRoles} crumb={crumb} personName={personName} personInit={personInit}>
      <div style={{ padding: '28px 36px 48px' }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontFamily: AT.display, fontSize: 32, fontWeight: 600, letterSpacing: '-0.02em' }}>
            {isAdmin ? 'Regional' : `${scopeRegion}`} <span style={{ color: AT.terra, fontStyle: 'italic' }}>performance</span>
          </div>
          <div style={{ marginTop: 6, fontSize: 13.5, color: AT.inkSoft }}>
            {allStores.length} store{allStores.length !== 1 ? 's' : ''} · {regions.length} region{regions.length !== 1 ? 's' : ''} · {totalAgents} agents
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 20 }}>
          <StatCard
            label={isAdmin ? 'Org avg score' : 'Region avg score'}
            value={orgAvg ?? '—'}
            unit={orgAvg !== null ? '/ 100' : undefined}
            accent={orgAvg !== null ? scoreColor(orgAvg) : AT.inkMuted}
            foot="Averaged across stores"
          />
          <StatCard label="Stores" value={allStores.length} unit="locations" accent={AT.butter} foot={regions.map((r) => r.region).join(' · ')} />
          <StatCard label="Total agents" value={totalAgents} unit="reps" accent={AT.sage} foot="Active this period" />
          {isAdmin && topRegion ? (
            <StatCard
              label="Top region"
              value={topRegion.region}
              unit={topRegion.rollup.avg_score !== null ? `avg ${topRegion.rollup.avg_score}` : undefined}
              accent={AT.terra}
              foot={REGION_NAMES[topRegion.region] ?? topRegion.region}
            />
          ) : (
            <StatCard
              label="Active agents"
              value={totalAgents}
              unit="reps"
              accent={AT.terra}
              foot="With at least one session"
            />
          )}
        </div>

        <div style={{ marginBottom: 22 }}>
          <SectionLabel>Regions</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(3, regions.length) || 1}, 1fr)`, gap: 14, marginTop: 12 }}>
            {regions.map((r) => (
              <RegionCard key={r.region} region={r} />
            ))}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 16, alignItems: 'start' }}>
          <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: 22 }}>
            <SectionLabel>Manager rollup — all stores</SectionLabel>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '28px 1fr 40px 1.1fr 60px 60px',
                gap: 12,
                alignItems: 'center',
                padding: '12px 2px 8px',
                fontFamily: AT.mono,
                fontSize: 9.5,
                color: AT.inkMuted,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                borderBottom: `1px solid ${AT.hair}`,
              }}
            >
              <div>#</div>
              <div>Store</div>
              <div>Reg</div>
              <div>Manager</div>
              <div>Score</div>
              <div>Sessions</div>
            </div>
            {ranked.length === 0 ? (
              <div style={{ padding: '24px 2px', color: AT.inkMuted, fontSize: 13 }}>No stores in view.</div>
            ) : (
              ranked.map((s, i) => (
                <div
                  key={s.store_id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '28px 1fr 40px 1.1fr 60px 60px',
                    gap: 12,
                    alignItems: 'center',
                    padding: '11px 2px',
                    borderBottom: i < ranked.length - 1 ? `1px solid ${AT.hairSoft}` : 'none',
                  }}
                >
                  <div style={{ fontFamily: AT.mono, fontSize: 12, color: AT.inkMuted }}>{i + 1}</div>
                  <div style={{ fontFamily: AT.display, fontSize: 14.5, fontWeight: 500 }}>{s.store_name}</div>
                  <div style={{ fontFamily: AT.mono, fontSize: 10.5, color: AT.inkSoft, fontWeight: 600 }}>{s.region}</div>
                  <div style={{ fontSize: 12.5, color: AT.inkSoft }}>{s.manager_name ?? '—'}</div>
                  <div style={{ fontFamily: AT.display, fontSize: 15, fontWeight: 700, color: s.rollup.avg_score !== null ? scoreColor(s.rollup.avg_score) : AT.inkMuted }}>
                    {s.rollup.avg_score ?? '—'}
                  </div>
                  <div style={{ fontFamily: AT.mono, fontSize: 12, color: AT.inkSoft }}>{s.rollup.total_sessions}</div>
                </div>
              ))
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <LeaderboardPanel title="Top performers" entries={topPerformers} color={AT.sage} />
            <LeaderboardPanel title="Needs attention" entries={bottomPerformers} color={AT.terra} />
          </div>
        </div>
      </div>
    </DashChrome>
  );
}

function RegionCard({ region }: { region: RegionSummary }) {
  const name = REGION_NAMES[region.region] ?? region.region;
  return (
    <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontFamily: AT.mono, fontSize: 11, letterSpacing: '0.14em', color: AT.inkSoft, fontWeight: 600, textTransform: 'uppercase' }}>{name}</div>
        {region.rollup.avg_score_delta !== null && (
          <div style={{ fontFamily: AT.mono, fontSize: 11, color: region.rollup.avg_score_delta >= 0 ? AT.sage : AT.terra, fontWeight: 600 }}>
            {region.rollup.avg_score_delta >= 0 ? '+' : ''}
            {region.rollup.avg_score_delta} {region.rollup.avg_score_delta >= 0 ? '▲' : '▼'}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 10 }}>
        <div style={{ fontFamily: AT.display, fontSize: 40, fontWeight: 700, color: region.rollup.avg_score !== null ? scoreColor(region.rollup.avg_score) : AT.inkMuted, letterSpacing: '-0.02em' }}>
          {region.rollup.avg_score ?? '—'}
        </div>
        <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkSoft }}>avg score</div>
      </div>
      <div style={{ marginTop: 12, display: 'flex', alignItems: 'flex-end', gap: 4, height: 32 }}>
        {region.stores.map((s) => (
          <div
            key={s.store_id}
            title={`${s.store_name} ${s.rollup.avg_score ?? '—'}`}
            style={{
              flex: 1,
              height: `${Math.max(15, s.rollup.avg_score ?? 15)}%`,
              background: s.rollup.avg_score !== null ? scoreColor(s.rollup.avg_score) : AT.hair,
              opacity: 0.85,
              borderRadius: 2,
            }}
          />
        ))}
      </div>
      <div style={{ marginTop: 8, fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted, letterSpacing: '0.08em' }}>
        {region.stores.length} stores · {region.rollup.active_agent_count} agents
      </div>
    </div>
  );
}

function LeaderboardPanel({ title, entries, color }: { title: string; entries: AgentLeaderboardEntry[]; color: string }) {
  return (
    <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: 20 }}>
      <SectionLabel>{title}</SectionLabel>
      <div style={{ display: 'flex', flexDirection: 'column', marginTop: 10 }}>
        {entries.length === 0 && <div style={{ fontSize: 12.5, color: AT.inkMuted, padding: '9px 2px' }}>Not enough data yet.</div>}
        {entries.map((a, i) => (
          <div
            key={a.user_id}
            style={{
              display: 'grid',
              gridTemplateColumns: '20px 34px 1fr auto',
              gap: 10,
              alignItems: 'center',
              padding: '9px 2px',
              borderBottom: i < entries.length - 1 ? `1px solid ${AT.hairSoft}` : 'none',
            }}
          >
            <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted }}>{i + 1}</div>
            <Avatar initial={initials(a.name)} color={color} />
            <div>
              <div style={{ fontFamily: AT.display, fontSize: 14, fontWeight: 500 }}>{a.name}</div>
              <div style={{ fontFamily: AT.mono, fontSize: 9.5, color: AT.inkMuted }}>{a.store_name ?? '—'}</div>
            </div>
            <div style={{ fontFamily: AT.display, fontSize: 16, fontWeight: 700, color }}>{a.avg_score}</div>
          </div>
        ))}
      </div>
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
