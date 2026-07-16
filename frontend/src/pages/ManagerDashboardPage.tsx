import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { fetchStoreStats } from '@/services/orgStatsService';
import { VT, scoreColor } from '@/styles/voiceprint';
import { Panel, PanelTitle, StickyNote, KpiCard, BlueprintTable, bpThStyle, bpTdStyle } from '@/components/voiceprint/primitives';
import {
  Avatar,
  CoreBar,
  DashChrome,
  formatLastActive,
  getEnabledRoles,
} from '@/components/dashboard/DashboardChrome';
import type { AgentLeaderboardEntry, StoreStatsResponse } from '@/types/orgStats';

const ADMIN_EMAILS = ['user@example.com'];
const STICKY_ROTATIONS = [-3, 2.5, -2, 1.5];

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
    return () => { cancelled = true; };
  }, [storeId, getValidToken]);

  const chrome = (children: React.ReactNode) => (
    <DashChrome
      role="Manager"
      enabledRoles={enabledRoles}
      title="MANAGER OFFICE"
      scribbleText="« rm 04 — site office"
      crumb={data ? `${data.store_name} · ${data.region} · ${data.leaderboard.length} agents` : undefined}
    >
      {children}
    </DashChrome>
  );

  if (!storeId) return chrome(<EmptyState message="Your account isn't assigned to a store yet." />);
  if (loading) return chrome(<LoadingState />);
  if (error || !data) return chrome(<EmptyState message={error ?? 'Failed to load stats'} />);

  const sorted = data.leaderboard; // already sorted by the API
  const atRisk = sorted.filter((a) => a.flag);
  const brightSpot = [...sorted]
    .filter((a) => a.weekly_delta !== null)
    .sort((a, b) => (b.weekly_delta ?? 0) - (a.weekly_delta ?? 0))[0];
  const showBrightSpot = brightSpot && (brightSpot.weekly_delta ?? 0) > 0;

  return chrome(
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <KpiCard
          label="Team avg"
          value={data.rollup.avg_score ?? '—'}
          color={data.rollup.avg_score != null ? scoreColor(data.rollup.avg_score) : undefined}
          sub={data.rollup.avg_score_delta != null ? `${data.rollup.avg_score_delta >= 0 ? '▲' : '▼'} ${Math.abs(data.rollup.avg_score_delta)} vs last week` : 'no history yet'}
        />
        <KpiCard label="At risk" value={atRisk.length} color={atRisk.length > 0 ? VT.hard : undefined} sub="flagged agents" />
        <KpiCard
          label="Store rank"
          value={data.store_rank != null ? <>{data.store_rank}<span style={{ fontSize: 14, color: VT.textMuted }}>/{data.store_count}</span></> : '—'}
          sub="company-wide"
        />
      </div>

      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={{ flex: 1.6, minWidth: 480 }}>
          <Panel>
            <PanelTitle dot={VT.amber}>
              Team roster — ranked by score
              <span style={{ marginLeft: 'auto', fontFamily: VT.mono, fontSize: 9 }}>SHEET A-04</span>
            </PanelTitle>
            {sorted.length === 0 ? (
              <div style={{ padding: '20px 0', color: VT.textMuted, fontSize: 13 }}>No agents assigned to this store yet.</div>
            ) : (
              <BlueprintTable>
                <thead>
                  <tr>
                    <th style={bpThStyle}>#</th>
                    <th style={bpThStyle}>Agent</th>
                    <th style={bpThStyle}>Score</th>
                    <th style={bpThStyle}>C·O·R·E</th>
                    <th style={bpThStyle}>Δ Week</th>
                    <th style={bpThStyle} />
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((a, i) => <RosterRow key={a.user_id} entry={a} rank={i + 1} />)}
                </tbody>
              </BlueprintTable>
            )}
          </Panel>
        </div>

        <div style={{ width: 320, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {atRisk.length === 0 && !showBrightSpot && (
            <div style={{ fontSize: 12.5, color: VT.textMuted }}>No agents currently flagged.</div>
          )}
          {atRisk.map((a, i) => (
            <StickyNote key={a.user_id} title={`Flag · ${a.name}`} width="100%" rotate={STICKY_ROTATIONS[i % STICKY_ROTATIONS.length]}>
              {a.flag}
            </StickyNote>
          ))}
          {showBrightSpot && (
            <StickyNote title="Bright spot ✓" width="100%" rotate={1.5} bright>
              {brightSpot!.name}&apos;s score is up {brightSpot!.weekly_delta} pts this week — best gain on the team.
            </StickyNote>
          )}
        </div>
      </div>
    </div>
  );
}

function RosterRow({ entry, rank }: { entry: AgentLeaderboardEntry; rank: number }) {
  const color = entry.avg_score != null ? scoreColor(entry.avg_score) : VT.textMuted;
  return (
    <tr>
      <td style={{ ...bpTdStyle, color: VT.textMuted }}>{String(rank).padStart(2, '0')}</td>
      <td style={bpTdStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Avatar initial={initials(entry.name)} color={color} />
          <div>
            <div style={{ fontFamily: VT.oswald, fontSize: 13, fontWeight: 500, color: VT.text }}>{entry.name}</div>
            <div style={{ fontSize: 9.5, color: VT.textMuted, marginTop: 1 }}>last active {formatLastActive(entry.last_active_at)}</div>
          </div>
        </div>
      </td>
      <td style={{ ...bpTdStyle, fontFamily: VT.anton, fontSize: 17, color }}>{entry.avg_score ?? '—'}</td>
      <td style={bpTdStyle}><CoreBar core={entry.core} /></td>
      <td style={{ ...bpTdStyle, color: (entry.weekly_delta ?? 0) >= 0 ? VT.rapport : VT.hard }}>
        {entry.weekly_delta != null ? `${entry.weekly_delta >= 0 ? '+' : ''}${entry.weekly_delta} ${entry.weekly_delta >= 0 ? '▲' : '▼'}` : '—'}
      </td>
      <td style={bpTdStyle}>{entry.flag ? <span style={{ color: VT.hard }}>⚑</span> : null}</td>
    </tr>
  );
}

function LoadingState() {
  return (
    <div style={{ padding: '80px 0', textAlign: 'center', fontFamily: VT.mono, fontSize: 11, color: VT.textMuted, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
      Loading…
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div style={{ padding: '80px 0', textAlign: 'center', color: VT.textMuted, fontSize: 14 }}>
      {message}
    </div>
  );
}
