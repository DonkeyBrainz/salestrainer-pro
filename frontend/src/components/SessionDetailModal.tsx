import React, { useEffect, useState } from 'react';
import { SessionDetail } from '@/types';
import { VT, scoreColor, TIER_LABEL } from '@/styles/voiceprint';
import { ModeTag, GradeCell, StickyNote } from '@/components/voiceprint/primitives';

interface SessionDetailModalProps {
  sessionId: string;
  onClose: () => void;
  onFetchSession: (sessionId: string) => Promise<SessionDetail>;
  /** Precomputed "Δ best" / "personal best" label from the archive table row, if known. */
  deltaLabel?: string | null;
}

const STAGE_ORDER = ['CONNECT', 'OBSERVE', 'RECOMMEND', 'EXECUTE'] as const;
const STAGE_LETTER: Record<string, string> = { CONNECT: 'C', OBSERVE: 'O', RECOMMEND: 'R', EXECUTE: 'E' };
const STAGE_NAME: Record<string, string> = { CONNECT: 'Connect', OBSERVE: 'Observe', RECOMMEND: 'Recommend', EXECUTE: 'Execute' };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase();
}

function formatLen(seconds: number | null): string {
  if (!seconds) return '—';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const SessionDetailModal: React.FC<SessionDetailModalProps> = ({ sessionId, onClose, onFetchSession, deltaLabel }) => {
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    onFetchSession(sessionId)
      .then((d) => { if (!cancelled) setDetail(d); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load session'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sessionId, onFetchSession]);

  useEffect(() => {
    const id = requestAnimationFrame(() => setOpen(true));
    return () => cancelAnimationFrame(id);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const backdropStyle: React.CSSProperties = {
    position: 'fixed', inset: 0, zIndex: 100,
    background: 'rgba(4,10,20,0.88)', backdropFilter: 'blur(4px)',
    opacity: open ? 1 : 0, transition: 'opacity .25s ease',
  };

  const wrapStyle: React.CSSProperties = {
    position: 'fixed', inset: 0, zIndex: 101,
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
  };

  const sheetStyle: React.CSSProperties = {
    width: '100%', maxWidth: 880, maxHeight: '86vh', overflowY: 'auto',
    background: `linear-gradient(180deg, ${VT.blueDeep}, #0c2140)`,
    border: `1px solid ${VT.lineFaint}`, padding: '32px 36px 36px', position: 'relative',
    transform: `translateY(${open ? 0 : 24}px) rotate(${open ? 0 : -0.4}deg)`,
    opacity: open ? 1 : 0,
    transition: 'transform .3s cubic-bezier(0.2,0.9,0.3,1.1), opacity .3s ease',
    boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
  };

  return (
    <div>
      <div style={backdropStyle} onClick={onClose} />
      <div style={wrapStyle}>
        <div style={sheetStyle}>
          <button
            onClick={onClose}
            style={{
              position: 'absolute', top: 20, right: 20,
              background: 'transparent', border: `1px solid ${VT.lineDim}`, color: VT.textMuted,
              fontFamily: VT.mono, fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase',
              padding: '6px 12px', cursor: 'pointer',
            }}
          >
            Close ✕
          </button>

          {loading && (
            <div style={{ padding: '60px 0', textAlign: 'center', fontFamily: VT.mono, fontSize: 11, color: VT.textMuted, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
              Loading session…
            </div>
          )}

          {!loading && (error || !detail) && (
            <div style={{ padding: '60px 0', textAlign: 'center', color: VT.hard, fontSize: 13 }}>
              {error || 'Session not found'}
            </div>
          )}

          {!loading && detail && (() => {
            const { session, transcript, evaluation } = detail;
            const mode = session.sessionType === 'evaluation' ? 'assess' : 'practice';
            return (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap', marginBottom: 24, paddingRight: 90 }}>
                  <div>
                    <div style={{ fontFamily: VT.anton, fontSize: 'clamp(20px,2.4vw,30px)', letterSpacing: '0.02em', color: VT.text }}>
                      {(session.personaName ?? 'Unknown').toUpperCase()} · {formatDate(session.startedAt)}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: VT.textMuted, flexWrap: 'wrap' }}>
                      <ModeTag mode={mode} />
                      <span>{formatLen(session.duration)}</span>
                      <span>regard: {TIER_LABEL[session.difficulty]?.toLowerCase() ?? session.difficulty}</span>
                      {deltaLabel && <span>{deltaLabel}</span>}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontFamily: VT.anton, fontSize: 58, lineHeight: 1, color: scoreColor(session.score) }}>
                      {session.score ?? '—'}
                    </div>
                    <div style={{ fontSize: 9, letterSpacing: '0.18em', color: VT.textMuted, textTransform: 'uppercase' }}>/ 100</div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
                  <div style={{ flex: 2, minWidth: 320 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted, borderBottom: `1px solid ${VT.lineFaint}`, paddingBottom: 8, marginBottom: 12 }}>
                      <span>Transcript — key exchange</span>
                      <span style={{ fontFamily: VT.mono }}>SHEET T-{session.startedAt.replace(/\D/g, '').slice(0, 8)}</span>
                    </div>
                    {transcript.messages.length === 0 && (
                      <div style={{ fontSize: 12, color: VT.textMuted }}>No transcript recorded for this session.</div>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {transcript.messages.map((m) => (
                        <div key={m.id} style={{ display: 'flex', gap: 10 }}>
                          <span style={{
                            width: 64, flexShrink: 0, fontSize: 8.5, letterSpacing: '0.1em', textTransform: 'uppercase',
                            color: m.role === 'user' ? VT.standard : VT.amber, paddingTop: 2,
                          }}>
                            {m.role === 'user' ? 'You' : (session.personaName ?? 'Customer')}
                          </span>
                          <span style={{ fontSize: 12, lineHeight: 1.6, color: VT.text }}>&ldquo;{m.text}&rdquo;</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div style={{ flex: 1, minWidth: 240, display: 'flex', flexDirection: 'column', gap: 20 }}>
                    <div>
                      <div style={{ fontSize: 9.5, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted, marginBottom: 10 }}>
                        C.O.R.E. grades
                      </div>
                      <div style={{ display: 'flex', gap: 8 }}>
                        {STAGE_ORDER.map((stage) => {
                          const stat = evaluation?.scorecard.stage_scores[stage];
                          const val = stat ? Math.round(stat.score) : null;
                          return (
                            <GradeCell
                              key={stage}
                              letter={STAGE_LETTER[stage]}
                              value={val ?? '—'}
                              name={STAGE_NAME[stage]}
                              color={scoreColor(val)}
                              compact
                            />
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted, marginBottom: 8 }}>
                        <span>Hints used</span>
                        <span style={{ fontFamily: VT.mono }}>{session.hintsUsed.length || 'NONE'}</span>
                      </div>
                      {session.hintsUsed.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {session.hintsUsed.map((h, i) => (
                            <div key={i} style={{ display: 'flex', gap: 8, fontSize: 10.5, lineHeight: 1.5 }}>
                              <span style={{ fontFamily: VT.mono, color: VT.amber, flexShrink: 0 }}>{h.t}</span>
                              <span style={{ color: VT.textMuted }}>{h.hint}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ fontSize: 10.5, color: VT.textMuted, letterSpacing: '0.02em', lineHeight: 1.6 }}>
                          {mode === 'assess'
                            ? 'Hints are disabled during assessments.'
                            : 'Ran clean — no hints requested.'}
                        </div>
                      )}
                    </div>

                    <StickyNote title="Coach note" width="100%" rotate={1.2}>
                      {evaluation?.summary ?? (session.hasEvaluation ? 'No summary recorded.' : 'This session was not graded.')}
                    </StickyNote>
                  </div>
                </div>
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
};

export default SessionDetailModal;
