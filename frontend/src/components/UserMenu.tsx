import React from 'react';
import { LogOut, Shield, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { AT } from '@/styles/tokens';
import { getEnabledRoles } from '@/components/dashboard/DashboardChrome';

// Admin user emails (same as backend)
const ADMIN_EMAILS = ['user@example.com'];

function pillButtonStyle(accent: string): React.CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 12px',
    borderRadius: 999,
    background: accent + '18',
    border: `1px solid ${accent}40`,
    color: accent,
    fontFamily: AT.mono,
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    cursor: 'pointer',
  };
}

const UserMenu: React.FC = () => {
  const { user, logout, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
  };

  const isAdmin = !!user && ADMIN_EMAILS.some((email) =>
    email.toLowerCase() === user.email?.toLowerCase()
  );

  const enabledRoles = getEnabledRoles(user, isAdmin);
  const hasManagerAccess = enabledRoles.includes('Manager');
  const hasAdminAccess = enabledRoles.includes('Admin');

  if (isLoading || !user) {
    return null;
  }

  const userInitial = user.name?.[0]?.toUpperCase() ?? '?';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {hasManagerAccess && (
        <button onClick={() => navigate('/team/manager')} style={pillButtonStyle(AT.sage)}>
          <Users size={14} />
          Team
        </button>
      )}
      {hasAdminAccess && (
        <button onClick={() => navigate('/team/admin')} style={pillButtonStyle(AT.butter)}>
          <Shield size={14} />
          Admin
        </button>
      )}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '4px 12px 4px 4px',
          borderRadius: 999,
          background: AT.surface,
          border: `1px solid ${AT.hair}`,
        }}
      >
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: '50%',
            background: AT.terra,
            color: AT.bg,
            display: 'grid',
            placeItems: 'center',
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          {userInitial}
        </div>
        <div style={{ fontSize: 13, fontWeight: 500, color: AT.ink }}>{user.name}</div>
      </div>
      <button onClick={handleLogout} style={pillButtonStyle(AT.inkSoft)}>
        <LogOut size={14} />
        Sign Out
      </button>
    </div>
  );
};

export default UserMenu;
