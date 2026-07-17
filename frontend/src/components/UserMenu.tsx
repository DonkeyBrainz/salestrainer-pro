import React from 'react';
import { LogOut, Shield, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { VT } from '@/styles/voiceprint';
import { NavTag } from '@/components/voiceprint/primitives';
import { getEnabledRoles } from '@/components/dashboard/DashboardChrome';

// Admin user emails (same as backend)
const ADMIN_EMAILS = ['user@example.com', 'miklpuerto69@gmail.com'];

function pillButtonStyle(accent: string): React.CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 12px',
    background: 'transparent',
    border: `1px solid ${accent}66`,
    color: accent,
    fontFamily: VT.mono,
    fontSize: 11,
    fontWeight: 500,
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
        <button onClick={() => navigate('/team/manager')} style={pillButtonStyle(VT.rapport)}>
          <Users size={14} />
          Team
        </button>
      )}
      {hasAdminAccess && (
        <button onClick={() => navigate('/team/admin')} style={pillButtonStyle(VT.amber)}>
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
          background: VT.bluePanel,
          border: `1px solid ${VT.lineFaint}`,
        }}
      >
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: '50%',
            background: VT.amber,
            color: '#1a1206',
            display: 'grid',
            placeItems: 'center',
            fontSize: 11,
            fontWeight: 700,
            fontFamily: VT.oswald,
          }}
        >
          {userInitial}
        </div>
        <div style={{ fontSize: 13, fontFamily: VT.mono, color: VT.text }}>{user.name}</div>
      </div>
      <NavTag onClick={handleLogout}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <LogOut size={14} />
          Sign Out
        </span>
      </NavTag>
    </div>
  );
};

export default UserMenu;
