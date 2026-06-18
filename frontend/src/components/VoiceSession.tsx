import React, { useEffect, useCallback, useState, useRef } from 'react';
import { AlertCircle, RefreshCw, Loader2, ArrowLeft } from 'lucide-react';
import { AppMode, ConnectionState, Persona } from '@/types';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAudio } from '@/hooks/useAudio';
import { fetchEvaluationPersonas, pickRandomPersona } from '@/services/personaService';
import ControlBar from './ControlBar';
import Transcript from './Transcript';
import CircularWaveform from './Visualizer';
import PersonaSelector from './PersonaSelector';
import CoachHUD from './CoachHUD';
import CoreChecklist from './CoreChecklist';
import ReportCard from './ReportCard';
import { HUDPanel } from './CoachHUD';
import { AT } from '@/styles/tokens';

interface VoiceSessionProps {
  mode: AppMode;
  onBack: () => void;
}

// ── Small HUD: customer mood bar ──────────────────────────────────────────────
function MoodHUD() {
  return (
    <div style={{ position: 'absolute', top: 24, left: 24, width: 240, zIndex: 10 }}>
      <HUDPanel title="Customer mood" accent={AT.butter}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
          <div style={{ flex: 1, height: 8, borderRadius: 4, background: AT.hair, position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(90deg, ${AT.terra}, ${AT.butter}, ${AT.sage})` }} />
            <div style={{ position: 'absolute', left: '52%', top: -3, width: 3, height: 14, background: AT.ink, borderRadius: 1 }} />
          </div>
        </div>
        <div style={{
          display: 'flex', justifyContent: 'space-between', marginTop: 6,
          fontFamily: AT.mono, fontSize: 9.5, color: AT.inkMuted, letterSpacing: '0.06em',
        }}>
          <span>guarded</span>
          <span style={{ color: AT.sage }}>warming</span>
          <span>open</span>
        </div>
      </HUDPanel>
    </div>
  );
}

// ── Small HUD: live score ─────────────────────────────────────────────────────
function LiveScoreHUD({ completedItems, currentPhaseIdx }: { completedItems: string[]; currentPhaseIdx: number }) {
  const totalCompleted = completedItems.length;
  const totalPossible = 12; // 4 stages × 3 items
  const score = Math.round((totalCompleted / totalPossible) * 100);

  return (
    <div style={{ position: 'absolute', bottom: 24, left: 24, width: 240, zIndex: 10 }}>
      <HUDPanel title="Live score" accent={AT.terra}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 6 }}>
          <div style={{ fontFamily: AT.display, fontSize: 38, fontWeight: 700, color: AT.ink, lineHeight: 1, letterSpacing: '-0.025em' }}>
            {score}
          </div>
          <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted }}>/ 100</div>
          {totalCompleted > 0 && (
            <div style={{ marginLeft: 'auto', fontFamily: AT.mono, fontSize: 11, color: AT.sage, fontWeight: 600 }}>
              +{totalCompleted} ▲
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 4, marginTop: 10 }}>
          {[0, 1, 2, 3].map(i => (
            <div key={i} style={{
              flex: 1, height: 4, borderRadius: 2,
              background: i < currentPhaseIdx ? AT.terra : i === currentPhaseIdx ? AT.terra + '80' : AT.hair,
            }} />
          ))}
        </div>
        <div style={{ fontFamily: AT.mono, fontSize: 9.5, color: AT.inkMuted, letterSpacing: '0.1em', marginTop: 6 }}>
          {Math.min(currentPhaseIdx, 4)} of 4 phases cleared
        </div>
      </HUDPanel>
    </div>
  );
}

// ── Small HUD: watch for / objections ────────────────────────────────────────
function WatchForHUD({ personaName }: { personaName?: string }) {
  const objections = personaName ? [
    { text: 'Price concerns', level: 2 },
    { text: 'Needs to think about it', level: 2 },
    { text: 'Wants to include family', level: 1 },
  ] : [];

  if (objections.length === 0) return null;

  const levelColor = (l: number) => l >= 3 ? AT.terra : l === 2 ? AT.butter : AT.sage;

  return (
    <div style={{ position: 'absolute', bottom: 24, right: 24, width: 280, zIndex: 10 }}>
      <HUDPanel title="Watch for" accent={AT.butter}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
          {objections.map((obj, i) => (
            <div key={i} style={{
              display: 'grid', gridTemplateColumns: '1fr auto',
              gap: 10, alignItems: 'center', padding: '4px 0',
            }}>
              <div style={{ fontSize: 12, color: AT.ink }}>{obj.text}</div>
              <div style={{ display: 'flex', gap: 3 }}>
                {[0, 1, 2].map(j => (
                  <div key={j} style={{
                    width: 5, height: 10, borderRadius: 1,
                    background: j < obj.level ? levelColor(obj.level) : AT.hair,
                  }} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </HUDPanel>
    </div>
  );
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function SessionTimer({ isRunning }: { isRunning: boolean }) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (isRunning) {
      startRef.current = Date.now() - elapsed * 1000;
      const id = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startRef.current!) / 1000));
      }, 1000);
      return () => clearInterval(id);
    }
  }, [isRunning]);

  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const ss = String(elapsed % 60).padStart(2, '0');

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 12px', background: AT.bg,
      border: `1px solid ${AT.hair}`, borderRadius: 8,
    }}>
      <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted, letterSpacing: '0.14em' }}>T+</div>
      <div style={{ fontFamily: AT.mono, fontSize: 14, color: AT.ink, fontWeight: 600 }}>
        {mm}:{ss}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
const VoiceSession: React.FC<VoiceSessionProps> = ({ mode, onBack }) => {
  const [error, setError] = useState<string | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [isLoadingPersona, setIsLoadingPersona] = useState(mode === AppMode.EVALUATION);
  const [personaFetchError, setPersonaFetchError] = useState<string | null>(null);

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
    completedItems,
    currentStage,
    userTranscription,
    dismissHint,
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

  const handleRestart = useCallback(async () => {
    stopMic(); disconnect(); setError(null);
    try {
      const wsMode = mode === AppMode.TRAINING ? 'training' : 'evaluation';
      await Promise.all([connect(selectedPersona?.id, wsMode), startMic()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart');
      stopMic();
      disconnect();
    }
  }, [connect, disconnect, startMic, stopMic, selectedPersona, mode]);

  const handleBack = useCallback(() => {
    stopMic(); disconnect(); cleanupAudio(); onBack();
  }, [stopMic, disconnect, cleanupAudio, onBack]);

  const handleHint = useCallback(() => { recallHint(); }, [recallHint]);
  const handleEvaluate = useCallback(() => { stopMic(); requestEvaluation(); }, [stopMic, requestEvaluation]);
  const handlePersonaSelect = useCallback((persona: Persona) => { setSelectedPersona(persona); }, []);
  const handlePersonaCancel = useCallback(() => { onBack(); }, [onBack]);

  const showPersonaSelector = mode === AppMode.TRAINING && !selectedPersona;
  const showPersonaLoading = mode === AppMode.EVALUATION && isLoadingPersona;
  const showPersonaFetchError = mode === AppMode.EVALUATION && personaFetchError && !selectedPersona;
  const showSessionUI = selectedPersona && !showPersonaSelector && !showPersonaLoading && !showPersonaFetchError;

  const modeTitle = mode === AppMode.TRAINING ? 'Live Practice' : 'Performance Assessment';
  const personaInitial = selectedPersona?.name?.[0] ?? '?';
  const personaLabel = selectedPersona?.name ?? 'Guest';

  const currentPhaseIdx = ['CONNECT', 'OBSERVE', 'RECOMMEND', 'EXECUTE', 'COMPLETE'].indexOf(currentStage);
  const isSpeakingAI = isPlaying;

  // ── Persona selector ─────────────────────────────────────────────────────
  if (showPersonaSelector) {
    return (
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        background: AT.bg, color: AT.ink,
      }}>
        {/* Header strip for persona picker */}
        <div style={{
          height: 60, padding: '0 24px',
          display: 'flex', alignItems: 'center', gap: 18,
          background: AT.surface, borderBottom: `1px solid ${AT.hair}`,
          flexShrink: 0,
        }}>
          <button
            onClick={handlePersonaCancel}
            style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'transparent', border: `1px solid ${AT.hair}`,
              color: AT.ink, fontSize: 14, cursor: 'pointer',
              display: 'grid', placeItems: 'center',
            }}
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <div style={{ fontFamily: AT.mono, fontSize: 10, letterSpacing: '0.16em', color: AT.terra, fontWeight: 600, textTransform: 'uppercase' }}>
              Live Practice
            </div>
            <div style={{ fontFamily: AT.display, fontSize: 15, fontWeight: 600, marginTop: 1 }}>
              Choose a customer
            </div>
          </div>
        </div>
        <PersonaSelector onSelect={handlePersonaSelect} onCancel={handlePersonaCancel} />
      </div>
    );
  }

  // ── Loading / error states ────────────────────────────────────────────────
  if (showPersonaLoading) {
    return (
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: AT.bg,
      }}>
        <div style={{ textAlign: 'center' }}>
          <Loader2 style={{ width: 32, height: 32, color: AT.terra, margin: '0 auto 16px', animation: 'spin 1s linear infinite' }} />
          <p style={{ fontFamily: AT.mono, fontSize: 12, color: AT.inkMuted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Preparing your evaluation...
          </p>
        </div>
        <style>{`@keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (showPersonaFetchError) {
    return (
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: AT.bg, padding: 24,
      }}>
        <div style={{ textAlign: 'center', maxWidth: 420 }}>
          <AlertCircle style={{ width: 48, height: 48, color: AT.terra, margin: '0 auto 16px' }} />
          <h3 style={{ fontFamily: AT.display, fontSize: 22, fontWeight: 600, color: AT.ink, marginBottom: 8 }}>
            Unable to Load Evaluation
          </h3>
          <p style={{ color: AT.inkSoft, fontSize: 14, marginBottom: 24 }}>{personaFetchError}</p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button
              onClick={loadEvaluationPersona}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 24px', borderRadius: 8,
                background: AT.terra, color: AT.bg,
                border: 'none', fontFamily: AT.sans,
                fontWeight: 600, cursor: 'pointer',
              }}
            >
              <RefreshCw size={14} /> Try Again
            </button>
            <button
              onClick={onBack}
              style={{
                padding: '10px 24px', borderRadius: 8,
                background: AT.surface2, color: AT.ink,
                border: `1px solid ${AT.hair}`,
                fontFamily: AT.sans, cursor: 'pointer',
              }}
            >
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Live session UI ───────────────────────────────────────────────────────
  return (
    <div style={{
      position: 'absolute', inset: 0,
      display: 'flex', flexDirection: 'column',
      background: AT.bg, color: AT.ink, fontFamily: AT.sans,
    }}>
      {/* Mission bar */}
      <div style={{
        padding: '14px 24px',
        borderBottom: `1px solid ${AT.hair}`,
        display: 'flex', alignItems: 'center', gap: 18,
        background: AT.surface, flexShrink: 0,
      }}>
        <button
          onClick={handleBack}
          style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'transparent', border: `1px solid ${AT.hair}`,
            color: AT.ink, cursor: 'pointer',
            display: 'grid', placeItems: 'center',
          }}
        >
          <ArrowLeft size={16} />
        </button>

        <div>
          <div style={{ fontFamily: AT.mono, fontSize: 10, letterSpacing: '0.16em', color: AT.terra, fontWeight: 600, textTransform: 'uppercase' }}>
            {connectionState === ConnectionState.CONNECTED ? '● Live session' : modeTitle}
          </div>
          <div style={{ fontFamily: AT.display, fontSize: 15, fontWeight: 600, marginTop: 1, color: AT.ink }}>
            {modeTitle}
            {selectedPersona?.name && (
              <span style={{ color: AT.inkMuted, fontWeight: 400 }}> · {selectedPersona.name}</span>
            )}
          </div>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 14 }}>
          {isConnected && <SessionTimer isRunning={isConnected} />}

          {/* Mic status */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontFamily: AT.mono, fontSize: 11, color: AT.inkSoft,
            textTransform: 'uppercase', letterSpacing: '0.1em',
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: isMuted ? AT.terra : AT.sage,
              boxShadow: isMuted ? 'none' : `0 0 6px ${AT.sage}`,
            }} />
            {isMuted ? 'Muted' : 'Mic ready'}
          </div>

          {/* Error banner inline */}
          {error && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 12px', borderRadius: 8,
              background: AT.terra + '20',
              border: `1px solid ${AT.terra}40`,
              fontSize: 12, color: AT.terra,
            }}>
              <AlertCircle size={12} />
              <span>{error}</span>
              <button
                onClick={handleToggleConnect}
                style={{
                  background: 'none', border: 'none',
                  color: AT.terra, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 4,
                  fontFamily: AT.mono, fontSize: 10,
                  letterSpacing: '0.1em', textTransform: 'uppercase',
                }}
              >
                <RefreshCw size={10} /> Retry
              </button>
            </div>
          )}

          {/* End session button (only when connected) */}
          {isConnected && (
            <button
              onClick={handleToggleConnect}
              style={{
                padding: '7px 12px', borderRadius: 8,
                background: 'transparent',
                border: `1px solid ${AT.hair}`,
                color: AT.inkSoft, fontSize: 12,
                fontFamily: AT.mono, letterSpacing: '0.08em',
                cursor: 'pointer',
              }}
            >
              End session
            </button>
          )}
        </div>
      </div>

      {/* CORE segments bar — training mode only */}
      {mode === AppMode.TRAINING && showSessionUI && (
        <CoreChecklist currentStage={currentStage} completedItems={completedItems} />
      )}

      {/* Stage area */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}>
        {/* Faint grid bg */}
        <div style={{
          position: 'absolute', inset: 0,
          backgroundImage: `linear-gradient(${AT.hair} 1px, transparent 1px), linear-gradient(90deg, ${AT.hair} 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
          opacity: 0.25,
          pointerEvents: 'none',
        }} />

        {/* ── When disconnected: centered welcome ── */}
        {connectionState === ConnectionState.DISCONNECTED && !error && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 28,
          }}>
            <CircularWaveform
              analyser={null}
              isActive={false}
              initial={personaInitial}
              label={personaLabel}
            />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: AT.display, fontSize: 22, fontWeight: 600, color: AT.ink, marginBottom: 8 }}>
                Ready to Practice
              </div>
              <div style={{ fontFamily: AT.sans, fontSize: 14, color: AT.inkSoft, maxWidth: 400, lineHeight: 1.5 }}>
                {mode === AppMode.TRAINING
                  ? 'Click Start Practice to begin. You\'ll receive real-time coaching and on-screen hints.'
                  : 'Click Start Practice to begin your assessment. No coaching or hints will be provided.'}
              </div>
              <div style={{
                marginTop: 16, display: 'inline-flex', alignItems: 'center', gap: 8,
                fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted,
                letterSpacing: '0.12em', textTransform: 'uppercase',
              }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: AT.inkMuted }} />
                Microphone access required
              </div>
            </div>
          </div>
        )}

        {/* ── Connecting indicator ── */}
        {connectionState === ConnectionState.CONNECTING && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 20,
          }}>
            <CircularWaveform analyser={null} isActive={false} initial={personaInitial} label={personaLabel} />
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted,
              letterSpacing: '0.12em', textTransform: 'uppercase',
            }}>
              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite', color: AT.terra }} />
              Connecting to AI...
            </div>
          </div>
        )}

        {/* ── Connected: active stage ── */}
        {isConnected && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            gap: 28, padding: 40,
          }}>
            {/* Speaking indicator */}
            <div style={{
              fontFamily: AT.mono, fontSize: 11,
              letterSpacing: '0.18em',
              color: isSpeakingAI ? AT.terra : AT.inkMuted,
              fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 8,
              textTransform: 'uppercase',
              transition: 'color 0.2s',
            }}>
              <div
                className={isSpeakingAI ? 'pulse-dot' : ''}
                style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: isSpeakingAI ? AT.terra : AT.inkMuted,
                  boxShadow: isSpeakingAI ? `0 0 10px ${AT.terra}` : 'none',
                  transition: 'background 0.2s',
                }}
              />
              {isSpeakingAI ? `${personaLabel} · speaking` : 'Your turn — speak naturally'}
            </div>

            {/* Circular waveform */}
            <CircularWaveform
              analyser={isSpeakingAI ? outputAnalyser : inputAnalyser}
              isActive={isConnected}
              initial={personaInitial}
              label={personaLabel}
            />

            {/* Transcript in center */}
            {messages.length > 0 && (
              <div style={{ width: 620, maxWidth: '90%', maxHeight: 180, overflow: 'hidden', position: 'relative' }}>
                <Transcript messages={messages.slice(-2)} currentInput={currentInput} />
              </div>
            )}
          </div>
        )}

        {/* HUD overlays — training mode, connected */}
        {isConnected && mode === AppMode.TRAINING && (
          <>
            <MoodHUD />
            <CoachHUD hint={currentHint} onDismiss={dismissHint} />
            <LiveScoreHUD completedItems={completedItems} currentPhaseIdx={Math.max(0, currentPhaseIdx)} />
            <WatchForHUD personaName={selectedPersona?.name} />
          </>
        )}
      </div>

      {/* Transport bar */}
      {showSessionUI && (
        <ControlBar
          connectionState={connectionState}
          isMuted={isMuted}
          onToggleConnect={handleToggleConnect}
          onToggleMute={toggleMute}
          onRestart={handleRestart}
          onHint={handleHint}
          onEvaluate={mode === AppMode.EVALUATION ? handleEvaluate : undefined}
          isEvaluating={isEvaluating}
          isGeneratingHint={false}
          inputAnalyser={inputAnalyser}
          mode={mode}
        />
      )}

      {/* Report card overlay */}
      {evaluationResult && (
        <ReportCard evaluation={evaluationResult} messages={messages} onClose={clearEvaluation} />
      )}

      <style>{`@keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }`}</style>
    </div>
  );
};

export default VoiceSession;
