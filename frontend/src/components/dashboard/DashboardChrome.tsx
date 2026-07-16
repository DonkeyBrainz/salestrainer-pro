import React from 'react';
import { useNavigate } from 'react-router-dom';
import { VT } from '@/styles/voiceprint';
import { NavTag, Cta, Scribble } from '@/components/voiceprint/primitives';
import UserMenu from '@/components/UserMenu';
import type { User } from '@/types/auth';
import type { CoreBreakdown } from '@/types/orgStats';

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
    <div style={{ display: 'flex', gap: 6 }}>
      {roles.map((r) => {
        const isActive = r === active;
        const isEnabled = enabled.includes(r);
        return (
          <Cta
            key={r}
            variant={isActive ? 'active' : 'ghost'}
            disabled={!isEnabled}
            onClick={() => isEnabled && !isActive && navigate(routeFor[r])}
            style={{ padding: '7px 14px', fontSize: 10 }}
          >
            {r}
          </Cta>
        );
      })}
    </div>
  );
}

interface DashChromeProps {
  children: React.ReactNode;
  role: RoleTab;
  enabledRoles: RoleTab[];
  title: string;
  scribbleText: string;
  crumb?: string;
}

export function DashChrome({ children, role, enabledRoles, title, scribbleText, crumb }: DashChromeProps) {
  const navigate = useNavigate();
  return (
    <div style={{ width: '100%', minHeight: '100vh', color: VT.text }}>
      <div style={{ padding: '32px 40px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <NavTag lobby onClick={() => navigate('/')}>◂ Lobby</NavTag>
          <div style={{ fontFamily: VT.anton, fontSize: 'clamp(22px,2.6vw,36px)', color: VT.text }}>{title}</div>
          {crumb && (
            <div style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 6 }}>
              {crumb}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
          <Scribble>{scribbleText}</Scribble>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <RoleTabs active={role} enabled={enabledRoles} />
            <UserMenu />
          </div>
        </div>
      </div>
      <div style={{ padding: '4px 40px 48px' }}>{children}</div>
    </div>
  );
}

export function Avatar({ initial, color }: { initial: string; color: string }) {
  return (
    <div style={{
      width: 30, height: 30, background: `${color}22`, color, fontFamily: VT.oswald, fontSize: 12, fontWeight: 600,
      display: 'grid', placeItems: 'center', flexShrink: 0, border: `1px solid ${color}55`,
    }}>
      {initial}
    </div>
  );
}

/** Single fill bar sized by the average of the four C.O.R.E. sub-scores, per the archive/roster table spec. */
export function CoreBar({ core }: { core: CoreBreakdown | null }) {
  if (!core) return <div style={{ width: 76, height: 6 }} />;
  const avg = (core.connect + core.observe + core.recommend + core.execute) / 4;
  return (
    <div
      title={`C ${core.connect.toFixed(0)} · O ${core.observe.toFixed(0)} · R ${core.recommend.toFixed(0)} · E ${core.execute.toFixed(0)}`}
      style={{ width: 76, height: 6, background: 'rgba(255,255,255,0.1)' }}
    >
      <div style={{ width: `${Math.min(100, avg)}%`, height: '100%', background: VT.amber }} />
    </div>
  );
}

export function formatLastActive(iso: string | null): string {
  if (!iso) return 'Never';
  const diffMs = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diffMs / 86_400_000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return `${days}d ago`;
}
