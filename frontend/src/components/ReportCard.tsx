import React from 'react';
import { CheckCircle2, AlertTriangle, X, Award, User, Bot } from 'lucide-react';
import { EvaluationResult, Grade, Message, StageScore } from '@/types';

interface ReportCardProps {
  evaluation: EvaluationResult;
  messages: Message[];
  onClose: () => void;
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

const ReportCard: React.FC<ReportCardProps> = ({ evaluation, messages, onClose }) => {
  const { scorecard, grade, final_score, strengths, improvements, summary } = evaluation;
  const gradeStyle = GRADE_COLORS[grade];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-white rounded-2xl shadow-2xl mx-4">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-full text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-8 space-y-8">
          {/* Header: Grade + Score */}
          <div className="flex flex-col items-center text-center space-y-3">
            <Award className="w-8 h-8 text-stone-400" />
            <h2 className="text-2xl font-serif-display text-[#2C2825]">
              Session Report
            </h2>
            <div
              className={`w-20 h-20 rounded-full flex items-center justify-center ring-4 ${gradeStyle.bg} ${gradeStyle.text} ${gradeStyle.ring}`}
            >
              <span className="text-4xl font-bold">{grade}</span>
            </div>
            <p className="text-lg font-bold text-stone-700">
              {Math.round(final_score)} / 100
            </p>
            {summary && (
              <p className="text-sm text-stone-500 max-w-sm">{summary}</p>
            )}
          </div>

          {/* Stage Breakdown */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-widest text-stone-400">
              Stage Breakdown
            </h3>
            {STAGE_ORDER.map((key) => {
              const stage = scorecard.stage_scores[key];
              if (!stage) return null;
              return <StageRow key={key} stage={stage} />;
            })}
          </div>

          {/* Modifiers */}
          {(scorecard.pbm_bonus !== 0 ||
            scorecard.objection_penalty !== 0 ||
            scorecard.deviation_penalty !== 0) && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-widest text-stone-400">
                Modifiers
              </h3>
              <div className="grid grid-cols-3 gap-3 text-center">
                {scorecard.pbm_bonus !== 0 && (
                  <div className="p-3 rounded-lg bg-emerald-50">
                    <p className="text-xs text-stone-500">PBM Bonus</p>
                    <p className="text-sm font-bold text-emerald-600">
                      +{scorecard.pbm_bonus.toFixed(1)}
                    </p>
                  </div>
                )}
                {scorecard.objection_penalty !== 0 && (
                  <div className="p-3 rounded-lg bg-red-50">
                    <p className="text-xs text-stone-500">Objection</p>
                    <p className="text-sm font-bold text-red-600">
                      {scorecard.objection_penalty.toFixed(1)}
                    </p>
                  </div>
                )}
                {scorecard.deviation_penalty !== 0 && (
                  <div className="p-3 rounded-lg bg-red-50">
                    <p className="text-xs text-stone-500">Deviation</p>
                    <p className="text-sm font-bold text-red-600">
                      {scorecard.deviation_penalty.toFixed(1)}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Strengths */}
          {strengths.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-widest text-stone-400">
                Strengths
              </h3>
              <ul className="space-y-2">
                {strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-stone-700">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Improvements */}
          {improvements.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-widest text-stone-400">
                Areas for Improvement
              </h3>
              <ul className="space-y-2">
                {improvements.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-stone-700">
                    <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Session Transcript */}
          {messages.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-widest text-stone-400">
                Session Transcript
              </h3>
              <div className="space-y-3 max-h-80 overflow-y-auto rounded-lg border border-stone-200 p-4 bg-stone-50">
                {messages.map((msg) => (
                  <div key={msg.id} className="flex items-start gap-2">
                    {msg.role === 'user' ? (
                      <User className="w-4 h-4 text-stone-400 mt-0.5 flex-shrink-0" />
                    ) : (
                      <Bot className="w-4 h-4 text-[#8B5E3C] mt-0.5 flex-shrink-0" />
                    )}
                    <div className="min-w-0">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-stone-400">
                        {msg.role === 'user' ? 'You' : 'Guest'}
                      </span>
                      <p className="text-sm text-stone-700 leading-relaxed">
                        {msg.text}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Done button */}
          <div className="pt-2">
            <button
              onClick={onClose}
              className="w-full py-3 bg-[#2C2825] text-[#F9F8F6] rounded-full text-sm font-bold uppercase tracking-widest hover:bg-black transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportCard;
