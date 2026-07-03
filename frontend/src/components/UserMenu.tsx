import React from 'react';
import { LogOut, User, Shield, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

// Admin user emails (same as backend)
const ADMIN_EMAILS = [
  'user@example.com',
];

const UserMenu: React.FC = () => {
  const { user, logout, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
  };

  // Case-insensitive email check
  const isAdmin = user && ADMIN_EMAILS.some(email =>
    email.toLowerCase() === user.email?.toLowerCase()
  );

  const hasTeamAccess = user && (isAdmin || user.role === 'manager' || user.role === 'regional_director');

  // Debug logging
  React.useEffect(() => {
    if (user) {
      console.log('UserMenu - Current user:', user);
      console.log('UserMenu - User email:', user.email);
      console.log('UserMenu - Is admin?', isAdmin);
      console.log('UserMenu - Admin emails:', ADMIN_EMAILS);
    }
  }, [user, isAdmin]);

  if (isLoading || !user) {
    return null;
  }

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-3 px-4 py-2 bg-white/50 border border-stone-200 rounded-full">
        <User className="w-4 h-4 text-stone-500" />
        <span className="text-sm text-stone-600">{user.name}</span>
      </div>
      {hasTeamAccess && (
        <button
          onClick={() => navigate('/team')}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-100 hover:bg-emerald-200 rounded-full text-xs font-bold uppercase tracking-wider text-emerald-800 transition-all"
        >
          <Users className="w-4 h-4" />
          Team
        </button>
      )}
      {isAdmin && (
        <button
          onClick={() => navigate('/admin')}
          className="flex items-center gap-2 px-4 py-2 bg-amber-100 hover:bg-amber-200 rounded-full text-xs font-bold uppercase tracking-wider text-amber-800 transition-all"
        >
          <Shield className="w-4 h-4" />
          Admin
        </button>
      )}
      <button
        onClick={handleLogout}
        className="flex items-center gap-2 px-4 py-2 bg-stone-100 hover:bg-stone-200 rounded-full text-xs font-bold uppercase tracking-wider text-stone-600 transition-all"
      >
        <LogOut className="w-4 h-4" />
        Sign Out
      </button>
    </div>
  );
};

export default UserMenu;
