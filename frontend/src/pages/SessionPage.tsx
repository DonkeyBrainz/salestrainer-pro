import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import VoiceSession from '@/components/VoiceSession';
import { AppMode } from '@/types';
import { AT } from '@/styles/tokens';

const SessionPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const appMode = location.pathname === '/training' ? AppMode.TRAINING : AppMode.EVALUATION;

  const handleBack = () => {
    navigate('/');
  };

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: AT.bg, color: AT.ink,
      fontFamily: AT.sans,
      overflow: 'hidden',
    }}>
      <VoiceSession mode={appMode} onBack={handleBack} />
    </div>
  );
};

export default SessionPage;
