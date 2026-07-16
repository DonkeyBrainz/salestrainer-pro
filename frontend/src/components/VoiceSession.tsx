import React, { useEffect, useCallback, useState, useRef } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AppMode, ConnectionState, CustomerMood, CustomerMoodState, Persona } from '@/types';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAudio } from '@/hooks/useAudio';
import { fetchEvaluationPersonas, pickRandomPersona } from '@/services/personaService';
import PersonaSelector from './PersonaSelector';
import ReportCard from './ReportCard';
import { VT, TIER_LABEL } from '@/styles/voiceprint';
import { Panel, PanelTitle, StickyNote, NavTag, Cta, FrameLabel, Redact, Stamp, Scribble } from '@/components/voiceprint/primitives';
import SpeakerUnit from '@/components/voiceprint/SpeakerUnit';

interface VoiceSessionProps {
  mode: AppMode;
  onBack: () => void;
}

const MOOD_POSITION: Record<CustomerMood, number> = {
  frustrated: 6,
  skeptical: 28,
  neutral: 50,
  interested: 74,
  ready_to_buy: 94,
};

const STAGE_CONFIGS = [
  { key: 'CONNECT', letter: 'C', name: 'Connect', items: ['warm_greeting', 'establish_credibility', 'create_comfort'] },
  { key: 'OBSERVE', letter: 'O', name: 'Observe', items: ['needs_discovery', 'goal_identification', 'motivator_mapping'] },
  { key: 'RECOMMEND', letter: 'R', name: 'Recommend', items: ['solution_presentation', 'value_connection', 'risk_mitigation'] },
  { key: 'EXECUTE', letter: 'E', name: 'Execute', items: ['commitment_request', 'objection_handling', 'finalize_agreement'] },
] as const;

function useElapsedSeconds(isRunning: boolean, frozen: boolean) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (isRunning && !frozen) {
      if (startRef.current === null) startRef.current = Date.now() - elapsed * 1000;
      const id = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startRef.current!) / 1000));
      }, 1000);
      return () => clearInterval(id);
    }
    if (!isRunning) { startRef.current = null; setElapsed(0); }
  }, [isRunning, frozen]); // eslint-disable-line react-hooks/exhaustive-deps

  return elapsed;
}

function formatTimer(totalSeconds: number): string {
  const mm = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
  const ss = String(totalSeconds % 60).padStart(2, '0');
  return `${mm}:${ss}`;
}

function formatDuration(totalSeconds: number): string {
  const min = Math.floor(totalSeconds / 60);
  const sec = totalSeconds % 60;
  return `${min} min ${sec} s`;
}

function randomCaseFile(): string {
  return `VP-${Math.floor(1000 + Math.random() * 9000)}`;
}

// ── Left column: C.O.R.E. phases + live score (training only) ────────────────
function CorePhasesPanel({ currentStage, completedItems }: { currentStage: string; completedItems: string[] }) {
  return (
    <Panel>
      <PanelTitle dot={VT.amber}>C.O.R.E. phases</PanelTitle>
      {STAGE_CONFIGS.map((stage, i) => {
        const on = stage.key === currentStage;
        const completed = stage.items.filter((id) => completedItems.includes(id)).length;
        return (
          <div key={stage.key} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0',
            borderBottom: i < STAGE_CONFIGS.length - 1 ? `1px dashed ${VT.lineFaint}` : 'none',
            opacity: on ? 1 : 0.45,
          }}>
            <span style={{ fontFamily: VT.anton, fontSize: 14, width: 20, color: on ? VT.amber : VT.lineDim }}>{stage.letter}</span>
            <span style={{ fontFamily: VT.oswald, fontWeight: 600, fontSize: 12, letterSpacing: '0.1em', textTransform: 'uppercase', flex: 1 }}>{stage.name}</span>
            <span style={{ fontSize: 10, color: VT.textMuted }}>{completed}/{stage.items.length}</span>
          </div>
        );
      })}
    </Panel>
  );
}

function LiveScorePanel({ completedItems }: { completedItems: string[] }) {
  const score = Math.round((completedItems.length / 12) * 100);
  return (
    <Panel>
      <PanelTitle dot={VT.special}>Live score</PanelTitle>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ fontFamily: VT.anton, fontSize: 38, color: VT.line, lineHeight: 1 }}>{score}</span>
        <span style={{ fontSize: 11, color: VT.textMuted }}>/ 100</span>
      </div>
    </Panel>
  );
}

function DossierPanel() {
  const rows: [string, string][] = [
    ['Name', 'redacted redacted'],
    ['Profile', 'redacted profile line here'],
    ['Regard', 'redacted'],
    ['Objections', 'redacted · redacted · redac'],
  ];
  return (
    <Panel>
      <PanelTitle dot={VT.hard}>Subject dossier</PanelTitle>
      {rows.map(([key, val], i) => (
        <div key={key} style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', fontSize: 10.5,
          borderBottom: i < rows.length - 1 ? `1px dashed ${VT.lineFaint}` : 'none',
        }}>
          <span style={{ width: 74, flexShrink: 0, letterSpacing: '0.1em', textTransform: 'uppercase', color: VT.textMuted, fontSize: 8.5 }}>{key}</span>
          <Redact>{val}</Redact>
        </div>
      ))}
      <div style={{ fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 10 }}>
        Declassified after grading
      </div>
    </Panel>
  );
}

// ── Right column: mood + coach tip + watch-for (training) ────────────────────
function MoodPanel({ moodState }: { moodState: CustomerMoodState | null }) {
  const position = moodState ? MOOD_POSITION[moodState.mood] : 50;
  return (
    <Panel>
      <PanelTitle dot={VT.rapport}>Customer mood</PanelTitle>
      <div style={{ height: 6, background: VT.lineFaint, position: 'relative', marginTop: 4 }}>
        <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(90deg, ${VT.hard}, ${VT.amber}, ${VT.rapport})` }} />
        <div style={{ position: 'absolute', left: `${position}%`, top: -4, width: 2, height: 14, background: VT.line, transition: 'left 600ms ease-out' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, letterSpacing: '0.08em', color: VT.textMuted, textTransform: 'uppercase', marginTop: 6 }}>
        <span>guarded</span>
        <span style={{ color: VT.rapport }}>warming</span>
        <span>open</span>
      </div>
    </Panel>
  );
}

function WatchForPanel({ objections }: { objections: string[] }) {
  if (objections.length === 0) return null;
  return (
    <Panel>
      <PanelTitle dot={VT.hard}>Watch for</PanelTitle>
      {objections.slice(0, 4).map((obj, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '6px 0', fontSize: 11, lineHeight: 1.4 }}>
          <span style={{ width: 4, height: 10, background: VT.hard, flexShrink: 0, display: 'inline-block' }} />
          {obj}
        </div>
      ))}
    </Panel>
  );
}

function SealedRulesPanel() {
  return (
    <>
      <div style={{ border: `1px dashed ${VT.lineDim}`, padding: '14px 15px', textAlign: 'center' }}>
        <div style={{ fontFamily: VT.anton, fontSize: 22, letterSpacing: '0.12em', color: VT.lineDim }}>SEALED</div>
        <div style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 5, lineHeight: 1.6 }}>
          Score · mood read · coach notes<br />revealed after grading
        </div>
      </div>
      <Panel>
        <PanelTitle dot={VT.special}>Rules of the room</PanelTitle>
        <div style={{ fontSize: 10.5, lineHeight: 1.8, color: VT.textMuted }}>
          No hints · no transcript · no live score. Subject identity withheld. One take, graded end-to-end against C.O.R.E.
        </div>
      </Panel>
    </>
  );
}

const VoiceSession: React.FC<VoiceSessionProps> = ({ mode, onBack }) => {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [isLoadingPersona, setIsLoadingPersona] = useState(mode === AppMode.EVALUATION);
  const [personaFetchError, setPersonaFetchError] = useState<string | null>(null);
  const [caseFileId, setCaseFileId] = useState(randomCaseFile);
  const [hintPulseTick, setHintPulseTick] = useState(0);

  const {
    connectionState,
    isConnected,
    error: wsError,
    connect,
    disconnect,
    sendAudio,
    messages,
    currentInput,
    onAudioReceived,
    currentHint,
    moodState,
    completedItems,
    currentStage,
    recallHint,
    evaluationResult,
    isEvaluating,
    requestEvaluation,
    clearEvaluation,
  } = useWebSocket();

  const {
    startMic,
    stopMic,
    isMuted,
    toggleMute,
    inputAnalyser,
    outputAnalyser,
    playAudio,
    isPlaying,
    cleanup: cleanupAudio,
  } = useAudio(sendAudio);

  useEffect(() => {
    onAudioReceived.current = playAudio;
    return () => { onAudioReceived.current = null; };
  }, [onAudioReceived, playAudio]);

  const loadEvaluationPersona = useCallback(async () => {
    setIsLoadingPersona(true);
    setPersonaFetchError(null);
    try {
      const personas = await fetchEvaluationPersonas();
      const randomPersona = pickRandomPersona(personas);
      if (randomPersona) {
        setSelectedPersona(randomPersona);
      } else {
        setPersonaFetchError('No evaluation personas available');
      }
    } catch {
      setPersonaFetchError('Failed to load evaluation personas');
    } finally {
      setIsLoadingPersona(false);
    }
  }, []);

  useEffect(() => {
    if (mode === AppMode.EVALUATION) loadEvaluationPersona();
  }, [mode, loadEvaluationPersona]);

  useEffect(() => { if (wsError) setError(wsError); }, [wsError]);
  useEffect(() => { if (isConnected) setError(null); }, [isConnected]);
  useEffect(() => {
    return () => { stopMic(); disconnect(); cleanupAudio(); };
  }, [stopMic, disconnect, cleanupAudio]);

  const handleToggleConnect = useCallback(async () => {
    if (isConnected) {
      stopMic(); disconnect();
    } else {
      setError(null);
      try {
        const wsMode = mode === AppMode.TRAINING ? 'training' : 'evaluation';
        await Promise.all([connect(selectedPersona?.id, wsMode), startMic()]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start session');
        stopMic();
        disconnect();
      }
    }
  }, [isConnected, connect, disconnect, startMic, stopMic, selectedPersona, mode]);

  const handleRestart = useCallback(() => {
    stopMic(); disconnect(); cleanupAudio();
    clearEvaluation();
    setError(null);
    setCaseFileId(randomCaseFile());
  }, [stopMic, disconnect, cleanupAudio, clearEvaluation]);

  const handleBack = useCallback(() => {
    stopMic(); disconnect(); cleanupAudio(); onBack();
  }, [stopMic, disconnect, cleanupAudio, onBack]);

  const handleHint = useCallback(() => {
    recallHint();
    setHintPulseTick((t) => t + 1);
  }, [recallHint]);

  const handleEvaluate = useCallback(() => { stopMic(); requestEvaluation(); }, [stopMic, requestEvaluation]);
  const handlePersonaSelect = useCallback((persona: Persona) => { setSelectedPersona(persona); }, []);
  const handlePersonaCancel = useCallback(() => { onBack(); }, [onBack]);

  const showPersonaSelector = mode === AppMode.TRAINING && !selectedPersona;
  const showPersonaLoading = mode === AppMode.EVALUATION && isLoadingPersona;
  const showPersonaFetchError = mode === AppMode.EVALUATION && personaFetchError && !selectedPersona;
  const isAssessment = mode === AppMode.EVALUATION;
  const showResults = isAssessment && !!evaluationResult;

  const isSpeakingAI = isPlaying;
  const elapsed = useElapsedSeconds(isConnected, showResults);
  const [frozenDuration, setFrozenDuration] = useState<number | null>(null);
  useEffect(() => { if (showResults && frozenDuration === null) setFrozenDuration(elapsed); }, [showResults, elapsed, frozenDuration]);
  useEffect(() => { if (!showResults) setFrozenDuration(null); }, [showResults]);

  const personaName = selectedPersona?.name ?? 'Guest';

  if (showPersonaSelector) {
    return (
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column' }}>
        <PersonaSelector onSelect={handlePersonaSelect} onCancel={handlePersonaCancel} />
      </div>
    );
  }

  if (showPersonaLoading) {
    return (
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <Loader2 style={{ width: 32, height: 32, color: VT.amber, margin: '0 auto 16px', animation: 'spin 1s linear infinite' }} />
          <p style={{ fontFamily: VT.mono, fontSize: 12, color: VT.textMuted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Preparing your evaluation...
          </p>
        </div>
      </div>
    );
  }

  if (showPersonaFetchError) {
    return (
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ textAlign: 'center', maxWidth: 420 }}>
          <AlertCircle style={{ width: 48, height: 48, color: VT.hard, margin: '0 auto 16px' }} />
          <h3 style={{ fontFamily: VT.anton, fontSize: 22, color: VT.text, marginBottom: 8 }}>Unable to load evaluation</h3>
          <p style={{ color: VT.textMuted, fontSize: 14, marginBottom: 24 }}>{personaFetchError}</p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <Cta onClick={loadEvaluationPersona}>Try again</Cta>
            <Cta variant="ghost" onClick={onBack}>Go back</Cta>
          </div>
        </div>
      </div>
    );
  }

  if (showResults && evaluationResult) {
    return (
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', padding: '40px 40px 26px' }}>
        <ReportCard
          evaluation={evaluationResult}
          personaName={evaluationResult.persona_name ?? 'the subject'}
          caseFileId={caseFileId}
          duration={formatDuration(frozenDuration ?? elapsed)}
          onRetry={handleRestart}
          onArchive={() => navigate('/history')}
          onLobby={handleBack}
        />
      </div>
    );
  }

  const connecting = connectionState === ConnectionState.CONNECTING;
  const transcriptQuote = currentInput || messages[messages.length - 1]?.text || '';

  return (
    <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', padding: '40px 40px 26px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <NavTag lobby onClick={handleBack}>◂ Customers</NavTag>
          <div style={{ fontFamily: VT.anton, fontSize: 'clamp(22px,2.6vw,36px)', color: VT.text }}>
            {isAssessment ? 'PERFORMANCE ASSESSMENT' : 'LIVE PRACTICE'}
          </div>
          {isAssessment ? (
            <div style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 6 }}>
              Case file <b style={{ color: VT.amber, fontWeight: 500 }}>{caseFileId}</b> · Subject <Redact>confidential name</Redact> · Scenario <Redact>withheld until graded</Redact>
            </div>
          ) : (
            <div style={{ fontFamily: VT.caveat, fontSize: 20, color: VT.amber, marginLeft: 4, marginTop: -4, maxWidth: 480, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {personaName}{selectedPersona ? ` · ${selectedPersona.looking_for ?? ''} · ${TIER_LABEL[selectedPersona.difficulty]?.toLowerCase() ?? ''}` : ''}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
          {isAssessment && <Stamp kind="red">Confidential · no coaching</Stamp>}
          <Scribble>t+ {formatTimer(elapsed)}</Scribble>
        </div>
      </div>

      {error && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, padding: '8px 14px',
          border: `1px solid ${VT.hard}66`, background: 'rgba(228,87,74,0.1)', fontSize: 12, color: VT.hard,
        }}>
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      <style>{`
        @media (max-width: 860px) {
          .vs-col { width: 100% !important; order: 2; }
          .vs-center { order: 1; min-width: 0 !important; }
        }
      `}</style>
      <div style={{ flex: 1, display: 'flex', gap: 30, marginTop: 14, minHeight: 0, alignItems: 'stretch', flexWrap: 'wrap' }}>
        <div className="vs-col" style={{ display: 'flex', flexDirection: 'column', gap: 14, width: 250, justifyContent: 'center' }}>
          {isAssessment
            ? <DossierPanel />
            : <><CorePhasesPanel currentStage={currentStage} completedItems={completedItems} /><LiveScorePanel completedItems={completedItems} /></>
          }
        </div>

        <div className="vs-center" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 14, minWidth: 280, overflowY: 'auto' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: VT.amber, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 7, height: 7, borderRadius: 2, background: VT.amber, boxShadow: `0 0 10px ${VT.amber}` }} />
            {isAssessment
              ? (isConnected ? (isSpeakingAI ? 'Subject · speaking' : 'Subject · listening') : 'Subject · standing by')
              : (isConnected ? (isSpeakingAI ? `${personaName} · speaking` : 'Your turn — speak naturally') : `${personaName} · standing by`)
            }
          </div>

          <div style={{ width: 'min(30vw,300px)', height: 'min(30vw,300px)', flexShrink: 0 }}>
            <SpeakerUnit analyser={isSpeakingAI ? outputAnalyser : inputAnalyser} isActive={isConnected} />
          </div>

          <FrameLabel>{isAssessment ? <>FIG. 04 — <b style={{ color: VT.text }}>ASSESSMENT CHANNEL</b> · UNASSISTED</> : <>FIG. 03 — <b style={{ color: VT.text }}>LIVE CHANNEL</b></>}</FrameLabel>

          <div style={{ maxWidth: 560, textAlign: 'center' }}>
            {isAssessment ? (
              <div style={{ filter: 'blur(5px)', opacity: 0.75, userSelect: 'none', pointerEvents: 'none', fontFamily: VT.oswald, fontWeight: 500, fontSize: 18, lineHeight: 1.5 }}>
                The subject&apos;s words are withheld on screen during assessment. Listen carefully, this text is not readable.
              </div>
            ) : (
              <div style={{ fontFamily: VT.oswald, fontWeight: 500, fontSize: 18, lineHeight: 1.5, letterSpacing: '0.01em' }}>
                {transcriptQuote || (isConnected ? 'Listening…' : 'Click Begin session to start practicing.')}
              </div>
            )}
            <div style={{ fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 10 }}>
              {isAssessment ? 'Transcription withheld — listen and run the full conversation' : (isConnected ? 'Your turn — speak naturally' : 'Microphone access required')}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            {!isConnected ? (
              <Cta onClick={handleToggleConnect} disabled={connecting}>
                {connecting ? 'Connecting…' : `▸ Begin ${isAssessment ? 'assessment' : 'session'}`}
              </Cta>
            ) : (
              <>
                <Cta variant={isMuted ? 'muted' : 'default'} onClick={toggleMute}>{isMuted ? '🔇 Unmute' : '🎤 Mute'}</Cta>
                {!isAssessment && <Cta variant="ghost" onClick={handleHint}>Hint</Cta>}
                <Cta variant="ghost" onClick={isAssessment ? handleEvaluate : handleToggleConnect} disabled={isAssessment && isEvaluating}>
                  {isAssessment ? (isEvaluating ? 'Grading…' : 'End & grade') : 'End session'}
                </Cta>
              </>
            )}
          </div>
        </div>

        <div className="vs-col" style={{ display: 'flex', flexDirection: 'column', gap: 14, width: 250, justifyContent: 'center' }}>
          {isAssessment ? <SealedRulesPanel /> : (
            <>
              <MoodPanel moodState={moodState} />
              <StickyNote key={hintPulseTick} title="Coach tip" rotate={1.5} width="100%" pulse={hintPulseTick > 0}>
                {currentHint?.hint ?? 'Hints will appear here once you start talking with the customer.'}
              </StickyNote>
              <WatchForPanel objections={selectedPersona?.objections ?? []} />
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default VoiceSession;
