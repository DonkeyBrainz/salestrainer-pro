import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2, AlertCircle } from 'lucide-react';
import { VT } from '@/styles/voiceprint';
import { Panel } from '@/components/voiceprint/primitives';

const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { handleCallback, isLoading, error, isAuthenticated } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      // OAuth error from Google
      navigate('/login', { replace: true });
      return;
    }

    if (code && state) {
      hasProcessed.current = true;
      handleCallback(code, state);
    } else {
      // Missing required params
      navigate('/login', { replace: true });
    }
  }, [searchParams, handleCallback, navigate]);

  // Redirect on successful auth
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  // Redirect on error after processing
  useEffect(() => {
    if (error && hasProcessed.current) {
      // Give user a moment to see the error
      const timer = setTimeout(() => {
        navigate('/login', { replace: true });
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [error, navigate]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: VT.text }}>
      <Panel style={{ width: '100%', maxWidth: 420, margin: '0 16px', padding: '48px 36px', textAlign: 'center' }}>
        {error ? (
          <>
            <AlertCircle size={40} style={{ color: VT.hard, marginBottom: 20 }} />
            <div style={{ fontFamily: VT.anton, fontSize: 22, color: VT.text, marginBottom: 10 }}>Authentication failed</div>
            <p style={{ color: VT.textMuted, fontSize: 13, marginBottom: 8 }}>{error}</p>
            <p style={{ color: VT.textMuted, fontSize: 11, fontFamily: VT.mono }}>Redirecting to login…</p>
          </>
        ) : (
          <>
            <Loader2 size={40} style={{ color: VT.amber, marginBottom: 20, animation: 'spin 1s linear infinite' }} />
            <div style={{ fontFamily: VT.anton, fontSize: 22, color: VT.text, marginBottom: 10 }}>Completing sign in</div>
            <p style={{ color: VT.textMuted, fontSize: 13 }}>Please wait while we verify your credentials…</p>
          </>
        )}
      </Panel>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default AuthCallback;
