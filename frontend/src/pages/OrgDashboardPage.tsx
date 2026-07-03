import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, Globe, MapPin, AlertCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { fetchNationalStats, fetchRegionStats, fetchStoreStats } from '@/services/orgStatsService';
import type {
  AgentLeaderboardEntry,
  NationalStatsResponse,
  OrgRollup,
  RegionStatsResponse,
  StoreStatsResponse,
  StoreSummary,
} from '@/types/orgStats';

// Same allowlist UserMenu uses to decide who gets a national view.
const ADMIN_EMAILS = ['user@example.com'];

type Scope =
  | { level: 'national' }
  | { level: 'region'; region: string }
  | { level: 'store'; storeId: string };

type ScopeData =
  | { kind: 'national'; scope: { level: 'national' }; data: NationalStatsResponse }
  | { kind: 'region'; scope: { level: 'region'; region: string }; data: RegionStatsResponse }
  | { kind: 'store'; scope: { level: 'store'; storeId: string }; data: StoreStatsResponse };

function rootScope(role: string | undefined, storeId: string | null | undefined, region: string | null | undefined, isAdmin: boolean): Scope | null {
  if (isAdmin) return { level: 'national' };
  if (role === 'regional_director' && region) return { level: 'region', region };
  if (role === 'manager' && storeId) return { level: 'store', storeId };
  return null;
}

function scopeTitle(scope: Scope): string {
  if (scope.level === 'national') return 'Organization';
  if (scope.level === 'region') return `${scope.region} Region`;
  return scope.storeId;
}

function scopeIcon(scope: Scope) {
  if (scope.level === 'national') return <Globe className="w-5 h-5 text-[#8B5E3C]" />;
  if (scope.level === 'region') return <MapPin className="w-5 h-5 text-[#8B5E3C]" />;
  return <Building2 className="w-5 h-5 text-[#8B5E3C]" />;
}

function RollupCards({ rollup }: { rollup: OrgRollup }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="bg-white rounded-xl p-6 border border-stone-200">
        <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 mb-1">Total Sessions</p>
        <p className="text-3xl font-serif-display text-[#2C2825]">{rollup.total_sessions}</p>
      </div>
      <div className="bg-white rounded-xl p-6 border border-stone-200">
        <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 mb-1">Avg Score</p>
        <p className="text-3xl font-serif-display text-[#2C2825]">{rollup.avg_score ?? '—'}</p>
      </div>
      <div className="bg-white rounded-xl p-6 border border-stone-200">
        <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400 mb-1">Active Agents</p>
        <p className="text-3xl font-serif-display text-[#2C2825]">{rollup.active_agent_count}</p>
      </div>
    </div>
  );
}

function LeaderboardTable({ entries }: { entries: AgentLeaderboardEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-stone-400 text-sm py-6 text-center">No agents in this scope yet.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-stone-200">
            <th className="text-left py-3 px-4 text-sm font-bold text-stone-600">Agent</th>
            <th className="text-left py-3 px-4 text-sm font-bold text-stone-600">Store</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Sessions</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Avg Score</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Streak</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.user_id} className="border-b border-stone-100 hover:bg-stone-50">
              <td className="py-3 px-4 font-medium">{entry.name}</td>
              <td className="py-3 px-4 text-stone-500">{entry.store_name ?? '—'}</td>
              <td className="py-3 px-4 text-right">{entry.total_sessions}</td>
              <td className="py-3 px-4 text-right">{entry.avg_score ?? '—'}</td>
              <td className="py-3 px-4 text-right">{entry.current_streak}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StoreBreakdownTable({ stores, onSelect }: { stores: StoreSummary[]; onSelect: (storeId: string) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-stone-200">
            <th className="text-left py-3 px-4 text-sm font-bold text-stone-600">Store</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Sessions</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Avg Score</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Active Agents</th>
          </tr>
        </thead>
        <tbody>
          {stores.map((store) => (
            <tr
              key={store.store_id}
              onClick={() => onSelect(store.store_id)}
              className="border-b border-stone-100 hover:bg-stone-50 cursor-pointer transition-colors"
            >
              <td className="py-3 px-4 font-medium">{store.store_name}</td>
              <td className="py-3 px-4 text-right">{store.rollup.total_sessions}</td>
              <td className="py-3 px-4 text-right">{store.rollup.avg_score ?? '—'}</td>
              <td className="py-3 px-4 text-right">{store.rollup.active_agent_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RegionBreakdownTable({
  regions,
  onSelect,
}: {
  regions: NationalStatsResponse['regions'];
  onSelect: (region: string) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-stone-200">
            <th className="text-left py-3 px-4 text-sm font-bold text-stone-600">Region</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Stores</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Sessions</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Avg Score</th>
            <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Active Agents</th>
          </tr>
        </thead>
        <tbody>
          {regions.map((region) => (
            <tr
              key={region.region}
              onClick={() => onSelect(region.region)}
              className="border-b border-stone-100 hover:bg-stone-50 cursor-pointer transition-colors"
            >
              <td className="py-3 px-4 font-medium">{region.region}</td>
              <td className="py-3 px-4 text-right">{region.stores.length}</td>
              <td className="py-3 px-4 text-right">{region.rollup.total_sessions}</td>
              <td className="py-3 px-4 text-right">{region.rollup.avg_score ?? '—'}</td>
              <td className="py-3 px-4 text-right">{region.rollup.active_agent_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const OrgDashboardPage: React.FC = () => {
  const { user, getValidToken } = useAuth();
  const navigate = useNavigate();

  const isAdmin = !!user && ADMIN_EMAILS.some((e) => e.toLowerCase() === user.email?.toLowerCase());
  const root = rootScope(user?.role, user?.storeId, user?.region, isAdmin);

  const [stack, setStack] = useState<Scope[]>(root ? [root] : []);
  const [result, setResult] = useState<ScopeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const currentScope = stack[stack.length - 1] ?? null;

  const load = useCallback(async (scope: Scope) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getValidToken();
      if (!token) {
        setError('Not authenticated');
        return;
      }
      if (scope.level === 'national') {
        const data = await fetchNationalStats(token);
        setResult({ kind: 'national', scope, data });
      } else if (scope.level === 'region') {
        const data = await fetchRegionStats(scope.region, token);
        setResult({ kind: 'region', scope, data });
      } else {
        const data = await fetchStoreStats(scope.storeId, token);
        setResult({ kind: 'store', scope, data });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, [getValidToken]);

  useEffect(() => {
    if (currentScope) load(currentScope);
  }, [currentScope, load]);

  if (!root) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-stone-50 to-amber-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-serif-display text-[#2C2825] mb-2">No Access</h2>
          <p className="text-stone-600 mb-6">
            This dashboard is for managers, regional directors, and admins.
          </p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-[#8B5E3C] hover:bg-[#6D4A2E] text-white rounded-full font-bold uppercase tracking-wider transition-colors"
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  const handleDrillIntoStore = (storeId: string) => setStack((prev) => [...prev, { level: 'store', storeId }]);
  const handleDrillIntoRegion = (region: string) => setStack((prev) => [...prev, { level: 'region', region }]);
  const handleBack = () => setStack((prev) => (prev.length > 1 ? prev.slice(0, -1) : prev));

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 to-amber-50">
      <div className="bg-white border-b border-stone-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => (stack.length > 1 ? handleBack() : navigate('/'))}
                className="p-2 hover:bg-stone-100 rounded-full transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-stone-600" />
              </button>
              <div className="flex items-center gap-2">
                {scopeIcon(currentScope!)}
                <div>
                  <h1 className="text-2xl font-serif-display text-[#2C2825]">{scopeTitle(currentScope!)}</h1>
                  <p className="text-sm text-stone-500">Team performance dashboard</p>
                </div>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-stone-600">{user?.name}</p>
              <p className="text-xs text-stone-400">{user?.email}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {loading && (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#8B5E3C]" />
          </div>
        )}

        {!loading && error && (
          <div className="bg-white rounded-xl p-6 border border-stone-200 text-center">
            <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
            <p className="text-stone-600">{error}</p>
          </div>
        )}

        {!loading && !error && result && (
          <>
            <RollupCards rollup={result.data.rollup} />

            {result.kind === 'national' && (
              <div className="bg-white rounded-xl p-6 border border-stone-200">
                <h2 className="text-xl font-serif-display text-[#2C2825] mb-4">Regions</h2>
                <RegionBreakdownTable regions={result.data.regions} onSelect={handleDrillIntoRegion} />
              </div>
            )}

            {result.kind === 'region' && (
              <div className="bg-white rounded-xl p-6 border border-stone-200">
                <h2 className="text-xl font-serif-display text-[#2C2825] mb-4">Stores</h2>
                <StoreBreakdownTable stores={result.data.stores} onSelect={handleDrillIntoStore} />
              </div>
            )}

            <div className="bg-white rounded-xl p-6 border border-stone-200">
              <h2 className="text-xl font-serif-display text-[#2C2825] mb-4">Agent Leaderboard</h2>
              <LeaderboardTable entries={result.data.leaderboard} />
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default OrgDashboardPage;
