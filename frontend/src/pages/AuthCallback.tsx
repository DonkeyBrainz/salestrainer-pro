import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2, AlertCircle } from 'lucide-react';
import AmbientBackground from '@/components/AmbientBackground';

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
    <div className="flex h-screen bg-[#F9F8F6] text-[#2C2825] font-sans overflow-hidden relative">
      <AmbientBackground mode={null} audioLevel={0} sentiment="neutral" />

      <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
        <div className="bg-white/80 backdrop-blur-md rounded-2xl p-12 border border-stone-200 shadow-xl max-w-md w-full mx-4 text-center">
          {error ? (
            <>
              <div className="flex justify-center mb-6">
                <div className="bg-red-50 p-4 rounded-full">
                  <AlertCircle className="w-10 h-10 text-red-500" />
                </div>
              </div>
              <h2 className="text-2xl font-serif-display text-[#2C2825] mb-4">
                Authentication Failed
              </h2>
              <p className="text-stone-500 mb-4">{error}</p>
              <p className="text-stone-400 text-sm">Redirecting to login...</p>
            </>
          ) : (
            <>
              <div className="flex justify-center mb-6">
                <Loader2 className="w-12 h-12 text-[#8B5E3C] animate-spin" />
              </div>
              <h2 className="text-2xl font-serif-display text-[#2C2825] mb-4">
                Completing Sign In
              </h2>
              <p className="text-stone-500">
                Please wait while we verify your credentials...
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthCallback;
