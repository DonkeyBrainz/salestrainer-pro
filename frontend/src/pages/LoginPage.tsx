import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { AlertCircle, Loader2 } from 'lucide-react';
import { AT } from '@/styles/tokens';

function ArenaLogo() {
  return (
    <div style={{ position: 'relative', width: 30, height: 30, flexShrink: 0 }}>
      <div style={{ position: 'absolute', inset: 0, background: AT.terra, transform: 'rotate(45deg)', borderRadius: 4 }} />
      <div style={{ position: 'absolute', inset: 6, background: AT.bg, transform: 'rotate(45deg)', borderRadius: 2 }} />
      <div style={{ position: 'absolute', inset: 11, background: AT.sage, transform: 'rotate(45deg)', borderRadius: 1 }} />
    </div>
  );
}

const LoginPage: React.FC = () => {
  const { login, isLoading, error, clearError } = useAuth();

  const handleGoogleLogin = async () => { clearError(); await login('google'); };
  const handleMicrosoftLogin = async () => { clearError(); await login('microsoft'); };

  return (
    <div style={{
      minHeight: '100vh', background: AT.bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: AT.sans,
      backgroundImage: `linear-gradient(${AT.hair} 1px, transparent 1px), linear-gradient(90deg, ${AT.hair} 1px, transparent 1px)`,
      backgroundSize: '40px 40px',
    }}>
      <div style={{
        background: AT.surface,
        border: `1px solid ${AT.hair}`,
        borderRadius: 18,
        padding: '48px 40px',
        width: '100%', maxWidth: 420,
        margin: '0 16px',
      }}>
        {/* Logo + title */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, marginBottom: 8 }}>
          <ArenaLogo />
          <div style={{ fontFamily: AT.display, fontSize: 20, fontWeight: 600, letterSpacing: '-0.01em' }}>
            SalesTrainer<span style={{ color: AT.terra, fontStyle: 'italic', fontWeight: 500 }}> Pro</span>
          </div>
        </div>

        <p style={{ textAlign: 'center', color: AT.inkMuted, fontSize: 13, marginBottom: 32, lineHeight: 1.5 }}>
          Sign in to access your practice sessions and performance assessments.
        </p>

        {/* Error */}
        {error && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '12px 14px', borderRadius: 8, marginBottom: 20,
            background: AT.terra + '18',
            border: `1px solid ${AT.terra}40`,
            color: AT.terra, fontSize: 13,
          }}>
            <AlertCircle size={14} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <button
            onClick={handleMicrosoftLogin}
            disabled={isLoading}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
              padding: '14px 20px',
              background: AT.terra, color: AT.bg,
              border: 'none', borderRadius: 10,
              fontFamily: AT.sans, fontWeight: 600, fontSize: 14,
              cursor: isLoading ? 'wait' : 'pointer',
              opacity: isLoading ? 0.7 : 1,
              boxShadow: `0 0 24px ${AT.terra}44`,
            }}
          >
            {isLoading ? (
              <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Redirecting…</>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 21 21">
                  <rect x="1" y="1" width="9" height="9" fill="#f25022" />
                  <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
                  <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
                  <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
                </svg>
                Sign in with Microsoft
              </>
            )}
          </button>

          <button
            onClick={handleGoogleLogin}
            disabled={isLoading}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
              padding: '14px 20px',
              background: AT.surface2, color: AT.ink,
              border: `1px solid ${AT.hair}`, borderRadius: 10,
              fontFamily: AT.sans, fontWeight: 500, fontSize: 14,
              cursor: isLoading ? 'wait' : 'pointer',
              opacity: isLoading ? 0.7 : 1,
            }}
          >
            {isLoading ? (
              <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Redirecting…</>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                Sign in with Google
              </>
            )}
          </button>
        </div>

        <p style={{ textAlign: 'center', color: AT.inkMuted, fontSize: 11, marginTop: 24, fontFamily: AT.mono, letterSpacing: '0.06em' }}>
          By signing in, you agree to the terms of service.
        </p>
      </div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default LoginPage;
