import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import VoiceSession from '@/components/VoiceSession';
import { AppMode } from '@/types';
import { VT } from '@/styles/voiceprint';

const SessionPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const appMode = location.pathname === '/training' ? AppMode.TRAINING : AppMode.EVALUATION;

  const handleBack = () => {
    navigate('/');
  };

  return (
    <div style={{
      minHeight: '100vh',
      color: VT.text,
    }}>
      <VoiceSession mode={appMode} onBack={handleBack} />
    </div>
  );
};

export default SessionPage;
