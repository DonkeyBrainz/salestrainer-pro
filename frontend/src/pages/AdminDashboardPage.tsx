import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { fetchNationalStats, fetchRegionStats } from '@/services/orgStatsService';
import { VT, scoreColor } from '@/styles/voiceprint';
import { Panel, PanelTitle, KpiCard, BlueprintTable, bpThStyle, bpTdStyle } from '@/components/voiceprint/primitives';
import { DashChrome } from '@/components/dashboard/DashboardChrome';
import type { AgentLeaderboardEntry, RegionSummary, StoreSummary } from '@/types/orgStats';

const ADMIN_EMAILS = ['user@example.com', 'miklpuerto69@gmail.com'];
const REGION_NAMES: Record<string, string> = { NC: 'North Carolina', SC: 'South Carolina', TX: 'Texas' };
const REGION_ACCENTS = [VT.rapport, VT.standard, VT.amber, VT.special, VT.hard];

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
            setCrumb('all regions');
          }
        } else if (scopeRegion) {
          const data = await fetchRegionStats(scopeRegion, token);
          if (!cancelled) {
            setRegions([{ region: data.region, rollup: data.rollup, stores: data.stores }]);
            setLeaderboard(data.leaderboard);
            setCrumb(`${data.region} region`);
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load stats');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
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
  const ranked = useMemo(
    () => [...allStores].sort((a, b) => (b.rollup.avg_score ?? -1) - (a.rollup.avg_score ?? -1)),
    [allStores]
  );
  const scoredLeaderboard = leaderboard.filter((e) => e.avg_score !== null);
  const topPerformers = scoredLeaderboard.slice(0, 5);
  const bottomPerformers = scoredLeaderboard.slice(-5).reverse();

  const chrome = (children: React.ReactNode) => (
    <DashChrome
      title="ADMIN WING"
      scribbleText="« rm 05 — the map table"
      crumb={regions ? `${crumb} · ${allStores.length} stores · ${totalAgents} agents` : undefined}
    >
      {children}
    </DashChrome>
  );

  if (!isAdmin && !scopeRegion) return chrome(<EmptyState message="This dashboard is for regional directors and admins." />);
  if (loading) return chrome(<LoadingState />);
  if (error || !regions) return chrome(<EmptyState message={error ?? 'Failed to load stats'} />);

  return chrome(
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <KpiCard
          label={isAdmin ? 'Org avg score' : 'Region avg score'}
          value={orgAvg ?? '—'}
          color={orgAvg != null ? scoreColor(orgAvg) : undefined}
          sub="averaged across stores"
        />
        <KpiCard label="Stores" value={allStores.length} sub={regions.map((r) => r.region).join(' · ')} />
        <KpiCard label="Total agents" value={totalAgents} sub="active this period" />
      </div>

      <div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {regions.map((r, i) => <RegionCard key={r.region} region={r} accent={REGION_ACCENTS[i % REGION_ACCENTS.length]} />)}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={{ flex: 1.6, minWidth: 480 }}>
          <Panel>
            <PanelTitle dot={VT.amber}>
              Store rollup — all regions
              <span style={{ marginLeft: 'auto', fontFamily: VT.mono, fontSize: 9 }}>SHEET A-05</span>
            </PanelTitle>
            {ranked.length === 0 ? (
              <div style={{ padding: '20px 0', color: VT.textMuted, fontSize: 13 }}>No stores in view.</div>
            ) : (
              <BlueprintTable>
                <thead>
                  <tr>
                    <th style={bpThStyle}>#</th>
                    <th style={bpThStyle}>Store</th>
                    <th style={bpThStyle}>Region</th>
                    <th style={bpThStyle}>Manager</th>
                    <th style={bpThStyle}>Agents</th>
                    <th style={bpThStyle}>Score</th>
                    <th style={bpThStyle}>Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {ranked.map((s, i) => (
                    <tr key={s.store_id}>
                      <td style={{ ...bpTdStyle, color: VT.textMuted }}>{String(i + 1).padStart(2, '0')}</td>
                      <td style={bpTdStyle}>{s.store_name}</td>
                      <td style={{ ...bpTdStyle, color: VT.textMuted }}>{s.region}</td>
                      <td style={{ ...bpTdStyle, color: VT.textMuted }}>{s.manager_name ?? '—'}</td>
                      <td style={{ ...bpTdStyle, color: VT.textMuted }}>{s.rollup.active_agent_count}</td>
                      <td style={{ ...bpTdStyle, fontFamily: VT.anton, fontSize: 17, color: s.rollup.avg_score != null ? scoreColor(s.rollup.avg_score) : VT.textMuted }}>
                        {s.rollup.avg_score ?? '—'}
                      </td>
                      <td style={{ ...bpTdStyle, color: (s.rollup.avg_score_delta ?? 0) >= 0 ? VT.rapport : VT.hard }}>
                        {s.rollup.avg_score_delta != null ? `${s.rollup.avg_score_delta >= 0 ? '+' : ''}${s.rollup.avg_score_delta} ${s.rollup.avg_score_delta >= 0 ? '▲' : '▼'}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </BlueprintTable>
            )}
          </Panel>
        </div>

        <div style={{ width: 320, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <SidePerfPanel title="Top performers" entries={topPerformers} color={VT.rapport} />
          <SidePerfPanel title="Needs attention" entries={bottomPerformers} color={VT.hard} />
        </div>
      </div>
    </div>
  );
}

function RegionCard({ region, accent }: { region: RegionSummary; accent: string }) {
  const name = REGION_NAMES[region.region] ?? region.region;
  return (
    <div style={{ flex: 1, minWidth: 180, background: VT.bluePanel, borderTop: `3px solid ${accent}`, border: `1px solid ${VT.lineFaint}`, borderTopWidth: 3, padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: accent, fontWeight: 600 }}>{name}</div>
        {region.rollup.avg_score_delta != null && (
          <div style={{ fontSize: 10.5, color: region.rollup.avg_score_delta >= 0 ? VT.rapport : VT.hard, fontWeight: 600 }}>
            {region.rollup.avg_score_delta >= 0 ? '+' : ''}{region.rollup.avg_score_delta} {region.rollup.avg_score_delta >= 0 ? '▲' : '▼'}
          </div>
        )}
      </div>
      <div style={{ fontFamily: VT.anton, fontSize: 30, marginTop: 8, color: region.rollup.avg_score != null ? scoreColor(region.rollup.avg_score) : VT.textMuted }}>
        {region.rollup.avg_score ?? '—'}
      </div>
      <div style={{ marginTop: 10, display: 'flex', alignItems: 'flex-end', gap: 4, height: 30 }}>
        {region.stores.map((s) => (
          <div
            key={s.store_id}
            title={`${s.store_name} ${s.rollup.avg_score ?? '—'}`}
            style={{
              flex: 1,
              height: `${Math.max(15, s.rollup.avg_score ?? 15)}%`,
              background: s.rollup.avg_score != null ? scoreColor(s.rollup.avg_score) : VT.lineDim,
              opacity: 0.85,
            }}
          />
        ))}
      </div>
      <div style={{ marginTop: 8, fontSize: 9, letterSpacing: '0.08em', color: VT.textMuted }}>
        {region.stores.length} stores · {region.rollup.active_agent_count} agents
      </div>
    </div>
  );
}

function SidePerfPanel({ title, entries, color }: { title: string; entries: AgentLeaderboardEntry[]; color: string }) {
  return (
    <Panel>
      <PanelTitle dot={color}>{title}</PanelTitle>
      {entries.length === 0 ? (
        <div style={{ fontSize: 11.5, color: VT.textMuted, padding: '4px 0' }}>Not enough data yet.</div>
      ) : (
        <BlueprintTable>
          <tbody>
            {entries.map((a, i) => (
              <tr key={a.user_id}>
                <td style={{ ...bpTdStyle, color: VT.textMuted, width: 18 }}>{i + 1}</td>
                <td style={bpTdStyle}>
                  <div style={{ fontFamily: VT.oswald, fontSize: 12.5, color: VT.text }}>{a.name}</div>
                  <div style={{ fontSize: 9, color: VT.textMuted }}>{a.store_name ?? '—'}</div>
                </td>
                <td style={{ ...bpTdStyle, fontFamily: VT.anton, fontSize: 15, color }}>{a.avg_score}</td>
              </tr>
            ))}
          </tbody>
        </BlueprintTable>
      )}
    </Panel>
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
