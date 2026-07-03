import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AT } from '@/styles/tokens';
import type { User } from '@/types/auth';

export function DashLogo() {
  return (
    <div style={{ position: 'relative', width: 26, height: 26 }}>
      <div style={{ position: 'absolute', inset: 0, background: AT.terra, transform: 'rotate(45deg)', borderRadius: 4 }} />
      <div style={{ position: 'absolute', inset: 5, background: AT.bg, transform: 'rotate(45deg)', borderRadius: 2 }} />
      <div style={{ position: 'absolute', inset: 10, background: AT.sage, transform: 'rotate(45deg)', borderRadius: 1 }} />
    </div>
  );
}

export type RoleTab = 'Agent' | 'Manager' | 'Admin';

/** Which role tabs this user can actually navigate into. */
export function getEnabledRoles(user: User | null, isAdmin: boolean): RoleTab[] {
  const roles: RoleTab[] = ['Agent'];
  if (user?.storeId) roles.push('Manager');
  if (isAdmin || user?.role === 'regional_director') roles.push('Admin');
  return roles;
}

export function RoleTabs({ active, enabled }: { active: RoleTab; enabled: RoleTab[] }) {
  const navigate = useNavigate();
  const roles: RoleTab[] = ['Agent', 'Manager', 'Admin'];
  const routeFor: Record<RoleTab, string> = { Agent: '/', Manager: '/team/manager', Admin: '/team/admin' };

  return (
    <div style={{ display: 'flex', gap: 4, padding: 3, background: AT.bg, border: `1px solid ${AT.hair}`, borderRadius: 9 }}>
      {roles.map((r) => {
        const isActive = r === active;
        const isEnabled = enabled.includes(r);
        return (
          <div
            key={r}
            onClick={() => isEnabled && !isActive && navigate(routeFor[r])}
            style={{
              padding: '6px 14px',
              borderRadius: 7,
              fontFamily: AT.mono,
              fontSize: 11,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              background: isActive ? AT.terra : 'transparent',
              color: isActive ? AT.bg : isEnabled ? AT.inkSoft : AT.inkMuted,
              fontWeight: 600,
              cursor: isEnabled && !isActive ? 'pointer' : 'default',
              opacity: isEnabled ? 1 : 0.4,
            }}
          >
            {r}
          </div>
        );
      })}
    </div>
  );
}

interface DashChromeProps {
  children: React.ReactNode;
  role: RoleTab;
  enabledRoles: RoleTab[];
  crumb?: string;
  personName: string;
  personInit: string;
}

export function DashChrome({ children, role, enabledRoles, crumb, personName, personInit }: DashChromeProps) {
  return (
    <div style={{ width: '100%', minHeight: '100vh', background: AT.bg, color: AT.ink, fontFamily: AT.sans, display: 'flex', flexDirection: 'column' }}>
      <div style={{ height: 62, padding: '0 28px', display: 'flex', alignItems: 'center', gap: 20, borderBottom: `1px solid ${AT.hair}`, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <DashLogo />
          <div style={{ fontFamily: AT.display, fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' }}>
            SalesTrainer<span style={{ color: AT.terra, fontStyle: 'italic', fontWeight: 500 }}> Pro</span>
          </div>
        </div>
        <div style={{ width: 1, height: 20, background: AT.hair }} />
        {crumb && (
          <div style={{ fontFamily: AT.mono, fontSize: 11.5, letterSpacing: '0.1em', color: AT.inkSoft, textTransform: 'uppercase' }}>
            {crumb}
          </div>
        )}
        <div style={{ marginLeft: 'auto' }} />
        <RoleTabs active={role} enabled={enabledRoles} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px 4px 4px', borderRadius: 999, background: AT.surface, border: `1px solid ${AT.hair}` }}>
          <div style={{ width: 24, height: 24, borderRadius: '50%', background: AT.terra, color: AT.bg, display: 'grid', placeItems: 'center', fontSize: 11, fontWeight: 700 }}>
            {personInit}
          </div>
          <div style={{ fontSize: 13, fontWeight: 500 }}>{personName}</div>
        </div>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>{children}</div>
    </div>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontFamily: AT.mono, fontSize: 10.5, letterSpacing: '0.18em', color: AT.inkMuted, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ display: 'inline-block', width: 14, height: 1, background: AT.terra }} />
      {String(children).toUpperCase()}
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  unit?: string;
  accent: string;
  delta?: string;
  deltaGood?: boolean;
  foot?: string;
}

export function StatCard({ label, value, unit, accent, delta, deltaGood, foot }: StatCardProps) {
  return (
    <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: '16px 18px' }}>
      <div style={{ fontFamily: AT.mono, fontSize: 10, letterSpacing: '0.16em', color: AT.inkMuted }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 6 }}>
        <div style={{ fontFamily: AT.display, fontSize: 34, color: accent, lineHeight: 1, fontWeight: 700, letterSpacing: '-0.02em' }}>{value}</div>
        {unit && <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkSoft }}>{unit}</div>}
        {delta && (
          <div style={{ marginLeft: 'auto', fontFamily: AT.mono, fontSize: 11.5, fontWeight: 600, color: deltaGood ? AT.sage : AT.terra }}>
            {delta}
          </div>
        )}
      </div>
      {foot && <div style={{ fontSize: 12, color: AT.inkMuted, marginTop: 10 }}>{foot}</div>}
    </div>
  );
}

export function CoreMini({ c, o, r, e }: { c: number; o: number; r: number; e: number }) {
  const vals = [
    { k: 'C', v: c, color: AT.sage },
    { k: 'O', v: o, color: AT.terra },
    { k: 'R', v: r, color: AT.butter },
    { k: 'E', v: e, color: '#7a8a85' },
  ];
  return (
    <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 22 }}>
      {vals.map((x) => (
        <div key={x.k} title={`${x.k} ${x.v.toFixed(0)}`} style={{ width: 6, height: `${Math.max(10, x.v)}%`, background: x.color, borderRadius: 1.5, opacity: 0.9 }} />
      ))}
    </div>
  );
}

export function Sparkline({ points, color }: { points: number[]; color: string }) {
  const w = 64;
  const h = 24;
  if (points.length < 2) {
    return <svg width={w} height={h} />;
  }
  const max = Math.max(...points);
  const min = Math.min(...points);
  const norm = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = h - ((p - min) / Math.max(1, max - min)) * h;
      return `${x},${y}`;
    })
    .join(' ');
  return (
    <svg width={w} height={h} style={{ overflow: 'visible' }}>
      <polyline points={norm} fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Avatar({ initial, color }: { initial: string; color: string }) {
  return (
    <div style={{ width: 34, height: 34, borderRadius: 9, background: color + '22', color, fontFamily: AT.display, fontSize: 14, fontWeight: 700, display: 'grid', placeItems: 'center', flexShrink: 0 }}>
      {initial}
    </div>
  );
}

export function scoreColor(v: number): string {
  if (v >= 82) return AT.sage;
  if (v < 65) return AT.terra;
  return AT.butter;
}

export function formatLastActive(iso: string | null): string {
  if (!iso) return 'Never';
  const diffMs = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diffMs / 86_400_000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return `${days}d ago`;
}
