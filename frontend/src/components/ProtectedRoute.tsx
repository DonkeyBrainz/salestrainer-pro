import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';
import AmbientBackground from '@/components/AmbientBackground';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen bg-[#F9F8F6] text-[#2C2825] font-sans overflow-hidden relative">
        <AmbientBackground mode={null} audioLevel={0} sentiment="neutral" />
        <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
          <Loader2 className="w-12 h-12 text-[#8B5E3C] animate-spin mb-4" />
          <p className="text-stone-500 text-lg">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
