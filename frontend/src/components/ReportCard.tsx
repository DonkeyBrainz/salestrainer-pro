import React from 'react';
import { EvaluationResult } from '@/types';
import { VT, scoreColor } from '@/styles/voiceprint';
import { StickyNote, Cta, FrameLabel, Stamp } from '@/components/voiceprint/primitives';

const STAGE_ORDER = [
  { key: 'CONNECT', letter: 'C', name: 'Connect' },
  { key: 'OBSERVE', letter: 'O', name: 'Observe' },
  { key: 'RECOMMEND', letter: 'R', name: 'Recommend' },
  { key: 'EXECUTE', letter: 'E', name: 'Execute' },
] as const;

interface ReportCardProps {
  evaluation: EvaluationResult;
  personaName: string;
  caseFileId: string;
  duration: string;
  onRetry: () => void;
  onArchive: () => void;
  onLobby: () => void;
}

/** Declassified scorecard shown after "End & grade" — the Voiceprint results view. */
const ReportCard: React.FC<ReportCardProps> = ({ evaluation, personaName, caseFileId, duration, onRetry, onArchive, onLobby }) => {
  const note = evaluation.summary
    || [evaluation.strengths[0], evaluation.improvements[0]].filter(Boolean).join(' ')
    || 'Session graded end-to-end against C.O.R.E.';

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 18, minHeight: 0, overflowY: 'auto' }}>
      <Stamp kind="green">Declassified · case file {caseFileId}</Stamp>
      <FrameLabel>FIG. 05 — <b style={{ color: VT.text }}>SCORECARD</b> · GRADED END-TO-END</FrameLabel>
      <div style={{ textAlign: 'center', margin: '8px 0 2px' }}>
        <div style={{ fontFamily: VT.anton, fontSize: 72, lineHeight: 1, color: VT.line, textShadow: '0 0 24px rgba(255,255,255,0.25)' }}>
          {Math.round(evaluation.final_score)}
        </div>
        <div style={{ fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 6 }}>
          {personaName} · assessment · {duration}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 14, width: 'min(560px,90%)' }}>
        {STAGE_ORDER.map((stage) => {
          const s = evaluation.scorecard.stage_scores[stage.key];
          const val = s ? Math.round(s.score) : null;
          return (
            <div key={stage.key} style={{ flex: 1, background: VT.bluePanel, border: `1px solid ${VT.lineFaint}`, padding: '14px 12px', textAlign: 'center' }}>
              <div style={{ fontFamily: VT.anton, fontSize: 15, color: VT.lineDim }}>{stage.letter}</div>
              <div style={{ fontFamily: VT.anton, fontSize: 32, marginTop: 4, color: val != null ? scoreColor(val) : VT.textMuted }}>{val ?? '—'}</div>
              <div style={{ fontSize: 8.5, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 3 }}>{stage.name}</div>
            </div>
          );
        })}
      </div>
      <StickyNote title="Grader's note" rotate={-1.5} width="min(380px,90%)">{note}</StickyNote>
      <div style={{ display: 'flex', gap: 12 }}>
        <Cta onClick={onRetry}>↺ Run it again</Cta>
        <Cta variant="ghost" onClick={onArchive}>File in archive ▸</Cta>
        <Cta variant="ghost" onClick={onLobby}>Lobby</Cta>
      </div>
    </div>
  );
};

export default ReportCard;
