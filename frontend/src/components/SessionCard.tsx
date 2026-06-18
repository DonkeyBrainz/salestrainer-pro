import React, { useState } from 'react';
import { SessionSummary } from '@/types';
import { Dumbbell, Trophy, Clock, User, MessageSquare } from 'lucide-react';
import { AT } from '@/styles/tokens';

interface SessionCardProps {
  session: SessionSummary;
  onClick: (sessionId: string) => void;
}

const SessionCard: React.FC<SessionCardProps> = ({ session, onClick }) => {
  const [hovered, setHovered] = useState(false);
  const isEvaluation = session.sessionType === 'evaluation';

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 60) return diffMins <= 1 ? 'Just now' : `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '—';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const gradeColor = (grade: string | null) => {
    if (!grade) return AT.inkMuted;
    switch (grade) {
      case 'A': return AT.sage;
      case 'B': return AT.sage;
      case 'C': return AT.butter;
      case 'D': return AT.terra;
      case 'F': return AT.terra;
      default: return AT.inkMuted;
    }
  };

  const diffColor = () => {
    switch (session.difficulty) {
      case 'high_regard': return AT.sage;
      case 'medium_regard': return AT.butter;
      case 'low_regard': return AT.terra;
      default: return AT.inkMuted;
    }
  };

  const diffLabel = () => {
    switch (session.difficulty) {
      case 'high_regard': return 'High regard';
      case 'medium_regard': return 'Med regard';
      case 'low_regard': return 'Low regard';
      default: return 'Unknown';
    }
  };

  return (
    <div
      onClick={() => onClick(session.sessionId)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: AT.surface,
        border: `1px solid ${hovered ? AT.hair : AT.hairSoft}`,
        borderRadius: 12, padding: '18px 20px',
        cursor: 'pointer',
        transition: 'border-color 0.15s, transform 0.15s',
        transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 10px', borderRadius: 6,
          background: isEvaluation ? AT.terra + '18' : AT.sage + '18',
          color: isEvaluation ? AT.terra : AT.sage,
          fontFamily: AT.mono, fontSize: 10,
          letterSpacing: '0.12em', textTransform: 'uppercase',
        }}>
          {isEvaluation ? <Trophy size={10} /> : <Dumbbell size={10} />}
          {session.sessionType}
        </div>
        <span style={{ fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted, letterSpacing: '0.08em' }}>
          {formatDate(session.startedAt)}
        </span>
      </div>

      {/* Persona */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 6,
          background: AT.surface2, color: AT.inkSoft,
          display: 'grid', placeItems: 'center',
        }}>
          <User size={14} />
        </div>
        <div style={{ fontFamily: AT.display, fontSize: 16, fontWeight: 500, color: AT.ink }}>
          {session.selectedPersona || 'Unknown Persona'}
        </div>
      </div>

      {/* Meta row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted }}>
          <Clock size={11} />{formatDuration(session.duration)}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted }}>
          <MessageSquare size={11} />{session.messageCount} msgs
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: AT.mono, fontSize: 10 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: diffColor() }} />
          <span style={{ color: AT.inkMuted }}>{diffLabel()}</span>
        </div>
      </div>

      {/* Score / grade */}
      {(session.score !== null || (session.hasEvaluation && session.grade)) && (
        <div style={{ paddingTop: 12, borderTop: `1px solid ${AT.hair}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {session.score !== null && (
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
              <span style={{ fontFamily: AT.display, fontSize: 28, fontWeight: 700, color: AT.ink }}>
                {session.score}
              </span>
              <span style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted }}>/100</span>
            </div>
          )}
          {session.hasEvaluation && session.grade && (
            <div style={{
              fontFamily: AT.display, fontSize: 28, fontWeight: 700,
              color: gradeColor(session.grade),
            }}>
              {session.grade}
            </div>
          )}
        </div>
      )}

      {/* Status chip */}
      {session.status !== 'completed' && (
        <div style={{ paddingTop: 10, borderTop: `1px solid ${AT.hair}` }}>
          <span style={{
            display: 'inline-block',
            padding: '3px 10px', borderRadius: 999,
            fontFamily: AT.mono, fontSize: 10,
            letterSpacing: '0.1em', textTransform: 'uppercase',
            background: AT.surface2, color: AT.inkMuted,
          }}>
            {session.status}
          </span>
        </div>
      )}
    </div>
  );
};

export default SessionCard;
