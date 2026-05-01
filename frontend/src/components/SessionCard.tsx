import React from 'react';
import { SessionSummary } from '@/types';
import { Dumbbell, Trophy, Clock, User, MessageSquare } from 'lucide-react';

interface SessionCardProps {
  session: SessionSummary;
  onClick: (sessionId: string) => void;
}

const SessionCard: React.FC<SessionCardProps> = ({ session, onClick }) => {
  const isEvaluation = session.sessionType === 'evaluation';

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return diffMins <= 1 ? 'Just now' : `${diffMins} minutes ago`;
    } else if (diffHours < 24) {
      return diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`;
    } else if (diffDays < 7) {
      return diffDays === 1 ? '1 day ago' : `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getGradeColor = (grade: string | null) => {
    if (!grade) return 'text-stone-400';
    switch (grade) {
      case 'A': return 'text-emerald-600';
      case 'B': return 'text-blue-600';
      case 'C': return 'text-amber-600';
      case 'D': return 'text-orange-600';
      case 'F': return 'text-red-600';
      default: return 'text-stone-400';
    }
  };

  return (
    <div
      onClick={() => onClick(session.sessionId)}
      className="group bg-white/80 backdrop-blur-md rounded-xl p-6 border border-stone-200 shadow-sm hover:shadow-xl transition-all cursor-pointer hover:-translate-y-0.5"
    >
      {/* Header: Type Badge + Date */}
      <div className="flex items-center justify-between mb-4">
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
          isEvaluation
            ? 'bg-red-50 text-red-600'
            : 'bg-amber-50 text-amber-700'
        }`}>
          {isEvaluation ? <Trophy className="w-3 h-3" /> : <Dumbbell className="w-3 h-3" />}
          {session.sessionType}
        </div>
        <span className="text-xs text-stone-400 uppercase tracking-wider">
          {formatDate(session.startedAt)}
        </span>
      </div>

      {/* Persona Name */}
      <div className="flex items-center gap-2 mb-3">
        <User className="w-4 h-4 text-stone-400" />
        <h3 className="font-serif-display text-lg text-stone-800">
          {session.selectedPersona || 'Unknown Persona'}
        </h3>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-3 gap-3 mb-4 text-sm">
        <div className="flex items-center gap-1.5 text-stone-500">
          <Clock className="w-3.5 h-3.5" />
          <span>{formatDuration(session.duration)}</span>
        </div>
        <div className="flex items-center gap-1.5 text-stone-500">
          <MessageSquare className="w-3.5 h-3.5" />
          <span>{session.messageCount} msgs</span>
        </div>
        <div className="flex items-center gap-1.5 text-stone-500">
          <span className={`w-2 h-2 rounded-full ${
            session.difficulty === 'high_regard' ? 'bg-emerald-500' :
            session.difficulty === 'medium_regard' ? 'bg-amber-500' :
            session.difficulty === 'low_regard' ? 'bg-red-500' :
            'bg-stone-500'
          }`} />
          <span className="text-xs">{
            session.difficulty === 'high_regard' ? 'High Regard' :
            session.difficulty === 'medium_regard' ? 'Medium Regard' :
            session.difficulty === 'low_regard' ? 'Low Regard' :
            'No Regard'
          }</span>
        </div>
      </div>

      {/* Grade/Score Display */}
      {(session.score !== null || (session.hasEvaluation && session.grade)) && (
        <div className="pt-3 border-t border-stone-200">
          <div className="flex items-center justify-between">
            <div className="flex flex-col gap-0.5">
              <span className="text-xs text-stone-400 uppercase tracking-wider">
                {session.hasEvaluation ? 'Grade' : 'Score'}
              </span>
              {session.score !== null && (
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-bold text-stone-700">
                    {session.score}
                  </span>
                  <span className="text-sm text-stone-400">/100</span>
                </div>
              )}
            </div>
            {session.hasEvaluation && session.grade && (
              <span className={`text-4xl font-serif-display font-bold ${getGradeColor(session.grade)}`}>
                {session.grade}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Status Badge (if not completed) */}
      {session.status !== 'completed' && (
        <div className="pt-3 border-t border-stone-200">
          <span className={`text-xs px-2 py-1 rounded-full uppercase tracking-wider font-bold ${
            session.status === 'active' ? 'bg-blue-50 text-blue-600' :
            session.status === 'paused' ? 'bg-amber-50 text-amber-600' :
            'bg-stone-100 text-stone-500'
          }`}>
            {session.status}
          </span>
        </div>
      )}
    </div>
  );
};

export default SessionCard;
