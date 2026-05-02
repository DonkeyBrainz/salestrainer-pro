import React, { useEffect, useState } from 'react';
import { X, User, Calendar, Clock, MessageSquare, Award, CheckCircle2, AlertTriangle } from 'lucide-react';
import { SessionDetail, Grade, StageScore } from '@/types';
import Transcript from './Transcript';

interface SessionDetailModalProps {
  sessionId: string;
  onClose: () => void;
  onFetchSession: (sessionId: string) => Promise<SessionDetail>;
}

const GRADE_COLORS: Record<Grade, { bg: string; text: string; ring: string }> = {
  A: { bg: 'bg-emerald-100', text: 'text-emerald-700', ring: 'ring-emerald-300' },
  B: { bg: 'bg-blue-100', text: 'text-blue-700', ring: 'ring-blue-300' },
  C: { bg: 'bg-amber-100', text: 'text-amber-700', ring: 'ring-amber-300' },
  D: { bg: 'bg-orange-100', text: 'text-orange-700', ring: 'ring-orange-300' },
  F: { bg: 'bg-red-100', text: 'text-red-700', ring: 'ring-red-300' },
};

const STAGE_ORDER = ['CONNECT', 'OBSERVE', 'RECOMMEND', 'EXECUTE'];
const STAGE_LABELS: Record<string, string> = {
  CONNECT: 'Connect',
  OBSERVE: 'Observe',
  RECOMMEND: 'Recommend',
  EXECUTE: 'Execute',
};

function ScoreBar({ score }: { score: number }) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const barColor =
    clampedScore >= 80
      ? 'bg-emerald-500'
      : clampedScore >= 60
        ? 'bg-blue-500'
        : clampedScore >= 40
          ? 'bg-amber-500'
          : 'bg-red-500';

  return (
    <div className="w-full h-2 bg-stone-200 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
        style={{ width: `${clampedScore}%` }}
      />
    </div>
  );
}

function StageRow({ stage }: { stage: StageScore }) {
  const label = STAGE_LABELS[stage.stage] || stage.stage;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold uppercase tracking-wider text-stone-600">
          {label}
        </span>
        <span className="text-sm font-bold text-stone-700">
          {Math.round(stage.score)}
        </span>
      </div>
      <ScoreBar score={stage.score} />
      {stage.feedback && (
        <p className="text-xs text-stone-500 mt-1">{stage.feedback}</p>
      )}
    </div>
  );
}

const SessionDetailModal: React.FC<SessionDetailModalProps> = ({ sessionId, onClose, onFetchSession }) => {
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        setLoading(true);
        const detail = await onFetchSession(sessionId);
        setSessionDetail(detail);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session');
      } finally {
        setLoading(false);
      }
    };

    fetchSession();
  }, [sessionId, onFetchSession]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
        <div className="bg-white rounded-2xl p-8 shadow-2xl">
          <p className="text-stone-600">Loading session...</p>
        </div>
      </div>
    );
  }

  if (error || !sessionDetail) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
        <div className="bg-white rounded-2xl p-8 shadow-2xl max-w-md">
          <p className="text-red-600 mb-4">{error || 'Session not found'}</p>
          <button
            onClick={onClose}
            className="w-full py-2 bg-stone-800 text-white rounded-lg hover:bg-black transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const { session, transcript, evaluation } = sessionDetail;
  const gradeStyle = evaluation?.grade ? GRADE_COLORS[evaluation.grade] : undefined;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-white rounded-2xl shadow-2xl mx-4 custom-scrollbar">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-full text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors z-10"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-8 space-y-8">
          {/* Session Summary */}
          <div className="space-y-4">
            <h2 className="text-3xl font-serif-display text-stone-800">Session Details</h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-2 text-sm">
                <User className="w-4 h-4 text-stone-400" />
                <div>
                  <p className="text-xs text-stone-400 uppercase tracking-wider">Persona</p>
                  <p className="text-stone-700 font-medium">{session.selectedPersona || 'Unknown'}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-sm">
                <Calendar className="w-4 h-4 text-stone-400" />
                <div>
                  <p className="text-xs text-stone-400 uppercase tracking-wider">Date</p>
                  <p className="text-stone-700 font-medium">{formatDate(session.startedAt)}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-stone-400" />
                <div>
                  <p className="text-xs text-stone-400 uppercase tracking-wider">Duration</p>
                  <p className="text-stone-700 font-medium">{formatDuration(session.duration)}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-sm">
                <MessageSquare className="w-4 h-4 text-stone-400" />
                <div>
                  <p className="text-xs text-stone-400 uppercase tracking-wider">Messages</p>
                  <p className="text-stone-700 font-medium">{session.messageCount}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Transcript */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-widest text-stone-400">Transcript</h3>
            <div className="border border-stone-200 rounded-xl overflow-hidden bg-[#F9F8F6] h-96">
              <Transcript messages={transcript.messages} readOnly={true} />
            </div>
          </div>

          {/* Evaluation (if exists) */}
          {evaluation && gradeStyle && (
            <div className="space-y-6 pt-6 border-t border-stone-200">
              <div className="flex items-center gap-3">
                <Award className="w-6 h-6 text-stone-400" />
                <h3 className="text-xl font-serif-display text-stone-800">Evaluation Results</h3>
              </div>

              {/* Grade + Score */}
              <div className="flex items-center gap-6">
                <div
                  className={`w-16 h-16 rounded-full flex items-center justify-center ring-4 ${gradeStyle.bg} ${gradeStyle.text} ${gradeStyle.ring}`}
                >
                  <span className="text-3xl font-bold">{evaluation.grade}</span>
                </div>
                <div>
                  <p className="text-sm text-stone-400 uppercase tracking-wider">Final Score</p>
                  <p className="text-2xl font-bold text-stone-700">
                    {Math.round(evaluation.final_score)} / 100
                  </p>
                </div>
              </div>

              {evaluation.summary && (
                <p className="text-sm text-stone-600 leading-relaxed">{evaluation.summary}</p>
              )}

              {/* Stage Breakdown */}
              <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-widest text-stone-400">
                  Stage Breakdown
                </h4>
                {STAGE_ORDER.map((key) => {
                  const stage = evaluation.scorecard.stage_scores[key];
                  if (!stage) return null;
                  return <StageRow key={key} stage={stage} />;
                })}
              </div>

              {/* Strengths */}
              {evaluation.strengths.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-widest text-stone-400">
                    Strengths
                  </h4>
                  <ul className="space-y-2">
                    {evaluation.strengths.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-stone-700">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Improvements */}
              {evaluation.improvements.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-widest text-stone-400">
                    Areas for Improvement
                  </h4>
                  <ul className="space-y-2">
                    {evaluation.improvements.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-stone-700">
                        <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Close button */}
          <div className="pt-2">
            <button
              onClick={onClose}
              className="w-full py-3 bg-[#2C2825] text-[#F9F8F6] rounded-full text-sm font-bold uppercase tracking-widest hover:bg-black transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SessionDetailModal;
