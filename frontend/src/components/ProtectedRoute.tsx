import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';
import { AT } from '@/styles/tokens';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{
        height: '100vh', background: AT.bg,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        fontFamily: AT.sans,
      }}>
        <Loader2 style={{ width: 32, height: 32, color: AT.terra, marginBottom: 16, animation: 'spin 1s linear infinite' }} />
        <p style={{ fontFamily: AT.mono, fontSize: 12, color: AT.inkMuted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Loading...
        </p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
