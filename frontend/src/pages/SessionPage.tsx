import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import VoiceSession from '@/components/VoiceSession';
import AmbientBackground from '@/components/AmbientBackground';
import { AppMode } from '@/types';

const SessionPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Map URL path to AppMode
  const appMode = location.pathname === '/training' ? AppMode.TRAINING : AppMode.EVALUATION;

  const handleBack = () => {
    navigate('/');
  };

  return (
    <div className="flex h-screen bg-[#F9F8F6] text-[#2C2825] font-sans overflow-hidden relative">
      <AmbientBackground mode={appMode} audioLevel={0} sentiment="neutral" />
      <VoiceSession mode={appMode} onBack={handleBack} />
    </div>
  );
};

export default SessionPage;
