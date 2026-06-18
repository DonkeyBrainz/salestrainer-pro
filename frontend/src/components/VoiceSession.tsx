import React, { useEffect, useCallback, useState } from 'react';
import { ArrowLeft, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';
import { AppMode, ConnectionState, Persona } from '@/types';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAudio } from '@/hooks/useAudio';
import { fetchEvaluationPersonas, pickRandomPersona } from '@/services/personaService';
import ControlBar from './ControlBar';
import Transcript from './Transcript';
import Visualizer from './Visualizer';
import PersonaSelector from './PersonaSelector';
import ProductSelector from './ProductSelector';
import CoachHUD from './CoachHUD';
import CoreChecklist from './CoreChecklist';
import ReportCard from './ReportCard';

interface VoiceSessionProps {
  mode: AppMode;
  onBack: () => void;
}

const VoiceSession: React.FC<VoiceSessionProps> = ({ mode, onBack }) => {
  const [error, setError] = useState<string | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [isLoadingPersona, setIsLoadingPersona] = useState(mode === AppMode.EVALUATION);
  const [personaFetchError, setPersonaFetchError] = useState<string | null>(null);
  const [selectedProductCategory, setSelectedProductCategory] = useState<string | null>(null);
  const [selectedProductType, setSelectedProductType] = useState<string | null>(null);
  const [productSelectionDone, setProductSelectionDone] = useState(false);

  // WebSocket hook for connection and messaging
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

  // Audio hook for mic capture and playback
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

  // Wire audio received callback
  useEffect(() => {
    onAudioReceived.current = playAudio;
    return () => {
      onAudioReceived.current = null;
    };
  }, [onAudioReceived, playAudio]);

  // Load random evaluation persona
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

  // For evaluation mode, randomly select a medium/hard persona on mount
  useEffect(() => {
    if (mode === AppMode.EVALUATION) {
      loadEvaluationPersona();
    }
  }, [mode, loadEvaluationPersona]);

  // Sync WebSocket error to local state (only when wsError is set, not when cleared)
  // This allows local errors (e.g., mic errors) to persist independently
  useEffect(() => {
    if (wsError) {
      setError(wsError);
    }
  }, [wsError]);

  // Clear error when connection succeeds
  useEffect(() => {
    if (isConnected) {
      setError(null);
    }
  }, [isConnected]);

  // Cleanup on unmount to prevent resource leaks
  useEffect(() => {
    return () => {
      stopMic();
      disconnect();
      cleanupAudio();
    };
  }, [stopMic, disconnect, cleanupAudio]);

  // Handle connect/disconnect toggle
  const handleToggleConnect = useCallback(async () => {
    if (isConnected) {
      stopMic();
      disconnect();
    } else {
      setError(null);
      try {
        const wsMode = mode === AppMode.TRAINING ? 'training' : 'evaluation';
        await Promise.all([
          connect(selectedPersona?.id, wsMode, selectedProductCategory ?? undefined, selectedProductType ?? undefined),
          startMic(),
        ]);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to start session';
        setError(errorMessage);
        stopMic();
        disconnect();
      }
    }
  }, [isConnected, connect, disconnect, startMic, stopMic, selectedPersona, selectedProductCategory, selectedProductType, mode]);

  // Handle restart - disconnect and reconnect
  const handleRestart = useCallback(async () => {
    stopMic();
    disconnect();
    setError(null);
    try {
      const wsMode = mode === AppMode.TRAINING ? 'training' : 'evaluation';
      await Promise.all([
        connect(selectedPersona?.id, wsMode, selectedProductCategory ?? undefined, selectedProductType ?? undefined),
        startMic(),
      ]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to restart session';
      setError(errorMessage);
      stopMic();
      disconnect();
    }
  }, [connect, disconnect, startMic, stopMic, selectedPersona, selectedProductCategory, selectedProductType, mode]);

  // Handle back navigation - cleanup first
  const handleBack = useCallback(() => {
    stopMic();
    disconnect();
    cleanupAudio();
    onBack();
  }, [stopMic, disconnect, cleanupAudio, onBack]);

  // Hint functionality - recall dismissed hint or trigger new one
  const handleHint = useCallback(() => {
    recallHint();
  }, [recallHint]);

  // Handle evaluate button click
  const handleEvaluate = useCallback(() => {
    stopMic();
    requestEvaluation();
  }, [stopMic, requestEvaluation]);

  // Handle persona selection (training mode)
  const handlePersonaSelect = useCallback((persona: Persona) => {
    setSelectedPersona(persona);
  }, []);

  // Handle persona selection cancel (go back)
  const handlePersonaCancel = useCallback(() => {
    onBack();
  }, [onBack]);

  // Handle product selection
  const handleProductSelect = useCallback((categoryId: string, typeId: string | null) => {
    setSelectedProductCategory(categoryId);
    setSelectedProductType(typeId);
    setProductSelectionDone(true);
  }, []);

  // Handle product selection skip
  const handleProductSkip = useCallback(() => {
    setProductSelectionDone(true);
  }, []);

  // Handle product selection back (return to persona selector)
  const handleProductBack = useCallback(() => {
    setSelectedPersona(null);
    setSelectedProductCategory(null);
    setSelectedProductType(null);
    setProductSelectionDone(false);
  }, []);

  // Get mode-specific title
  const modeTitle = mode === AppMode.TRAINING ? 'Live Practice' : 'Performance Assessment';

  // Show persona selector for training mode if no persona selected
  const showPersonaSelector = mode === AppMode.TRAINING && !selectedPersona;

  // Show product selector for training mode after persona selected but before product selection done
  const showProductSelector = mode === AppMode.TRAINING && selectedPersona && !productSelectionDone;

  // Show loading state for evaluation mode while fetching random persona
  const showPersonaLoading = mode === AppMode.EVALUATION && isLoadingPersona;

  // Show persona fetch error for evaluation mode
  const showPersonaFetchError = mode === AppMode.EVALUATION && personaFetchError && !selectedPersona;

  // Only show main session UI when persona is ready and product selection is done (or skipped)
  const showSessionUI = selectedPersona && !showPersonaSelector && !showProductSelector && !showPersonaLoading && !showPersonaFetchError;

  return (
    <div className="absolute inset-0 flex flex-col z-20">
      {/* Coach HUD - only show in Training mode */}
      {mode === AppMode.TRAINING && (
        <CoachHUD
          hint={currentHint}
          onDismiss={dismissHint}
        />
      )}

      {/* Header with back button */}
      <header className="px-6 py-4 flex items-center gap-4 bg-white/50 backdrop-blur-sm border-b border-stone-200">
        <button
          onClick={handleBack}
          className="p-2 rounded-full bg-white/50 backdrop-blur text-stone-600 hover:bg-stone-200 shadow-sm"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex flex-col">
          <h2 className="text-xl font-serif-display text-[#2C2825]">
            {modeTitle}
          </h2>
          {selectedPersona && (
            <span className="text-xs text-stone-500">
              Guest: {selectedPersona.name}
              {selectedProductCategory && ` | Product: ${selectedProductCategory}${selectedProductType ? ` / ${selectedProductType}` : ''}`}
            </span>
          )}
        </div>
        {/* Connection status badge */}
        {connectionState === ConnectionState.CONNECTED && (
          <span className="ml-auto px-3 py-1 bg-emerald-50 text-emerald-600 text-xs font-bold uppercase tracking-wider rounded-full flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            Live
          </span>
        )}
        {connectionState === ConnectionState.CONNECTING && (
          <span className="ml-auto px-3 py-1 bg-amber-50 text-amber-600 text-xs font-bold uppercase tracking-wider rounded-full flex items-center gap-1.5">
            <Loader2 className="w-3 h-3 animate-spin" />
            Connecting
          </span>
        )}
        {connectionState === ConnectionState.ERROR && (
          <span className="ml-auto px-3 py-1 bg-red-50 text-red-600 text-xs font-bold uppercase tracking-wider rounded-full flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full" />
            Error
          </span>
        )}
      </header>

      {/* Error banner with retry */}
      {error && (
        <div className="px-6 py-3 bg-red-50 border-b border-red-100 flex items-center gap-3 text-red-600">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="text-sm flex-1">{error}</span>
          <button
            onClick={handleToggleConnect}
            className="flex items-center gap-1 px-3 py-1 bg-red-100 hover:bg-red-200 rounded-full text-xs font-bold uppercase tracking-wider transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
          <button
            onClick={() => setError(null)}
            className="text-xs font-bold uppercase tracking-wider hover:text-red-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Persona selector for training mode */}
      {showPersonaSelector && (
        <PersonaSelector onSelect={handlePersonaSelect} onCancel={handlePersonaCancel} />
      )}

      {/* Product selector for training mode (after persona, before session) */}
      {showProductSelector && (
        <ProductSelector onSelect={handleProductSelect} onSkip={handleProductSkip} onBack={handleProductBack} />
      )}

      {/* Loading state for evaluation mode persona fetch */}
      {showPersonaLoading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 text-[#8B5E3C] animate-spin mx-auto mb-4" />
            <p className="text-stone-500">Preparing your evaluation...</p>
          </div>
        </div>
      )}

      {/* Persona fetch error for evaluation mode */}
      {showPersonaFetchError && (
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center max-w-md">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h3 className="text-xl font-serif-display text-[#2C2825] mb-3">
              Unable to Load Evaluation
            </h3>
            <p className="text-stone-500 mb-6">{personaFetchError}</p>
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={loadEvaluationPersona}
                className="flex items-center gap-2 px-6 py-2 bg-[#8B5E3C] hover:bg-[#7A5235] rounded-full text-sm font-bold uppercase tracking-wider text-white transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <button
                onClick={onBack}
                className="px-6 py-2 bg-stone-200 hover:bg-stone-300 rounded-full text-sm font-bold uppercase tracking-wider text-stone-600 transition-colors"
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main content area - only show after persona is selected */}
      {showSessionUI && (
        <>
          <div className="flex-1 flex overflow-hidden">
            {/* Left Sidebar - C.O.R.E. Checklist (training mode only) */}
            {mode === AppMode.TRAINING && (
              <div className="w-80 flex-shrink-0 px-4 py-6 overflow-y-auto bg-gradient-to-b from-[#F9F8F6] to-white border-r border-stone-200">
                <CoreChecklist
                  currentStage={currentStage}
                  completedItems={completedItems}
                />
              </div>
            )}

            {/* Main Content Column */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* AI Visualizer - shows when connected */}
              {isConnected && (
                <div className="h-24 px-6 py-4 flex items-center justify-center">
                  <div className="w-full max-w-md h-16">
                    <Visualizer
                      analyser={outputAnalyser}
                      isActive={isPlaying}
                      color="#8B5E3C"
                      variant="wave"
                    />
                  </div>
                </div>
              )}

              {/* Connecting indicator */}
              {connectionState === ConnectionState.CONNECTING && (
                <div className="h-24 px-6 py-4 flex items-center justify-center">
                  <div className="flex items-center gap-3 text-stone-500">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="text-sm">Connecting to AI assistant...</span>
                  </div>
                </div>
              )}

              {/* Welcome message - shows when disconnected */}
              {connectionState === ConnectionState.DISCONNECTED && !error && (
                <div className="flex-1 flex items-center justify-center px-6">
                  <div className="text-center max-w-md">
                    <h3 className="text-xl font-serif-display text-[#2C2825] mb-3">
                      Ready to Practice
                    </h3>
                    <p className="text-stone-500 mb-6">
                      {mode === AppMode.TRAINING
                        ? 'Click "Start Practice" to begin a live coached session. You\'ll receive real-time coaching and on-screen hints.'
                        : 'Click "Start Practice" to begin your assessment. No coaching or hints will be provided during this session.'}
                    </p>
                    <div className="flex items-center justify-center gap-2 text-xs text-stone-400 uppercase tracking-wider">
                      <span className="w-2 h-2 bg-stone-300 rounded-full" />
                      Microphone access required
                    </div>
                  </div>
                </div>
              )}

              {/* Transcript area - shows when connected or has messages */}
              {(isConnected || messages.length > 0) && (
                <div className="flex-1 overflow-hidden">
                  <Transcript messages={messages} currentInput={currentInput} />
                </div>
              )}
            </div>
          </div>

          {/* Control bar at bottom */}
          <div className="px-6 py-6 bg-gradient-to-t from-[#F9F8F6] via-[#F9F8F6] to-transparent">
            <div className="flex justify-center">
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
            </div>
          </div>
        </>
      )}
      {/* Report card overlay */}
      {evaluationResult && (
        <ReportCard evaluation={evaluationResult} messages={messages} onClose={clearEvaluation} />
      )}
    </div>
  );
};

export default VoiceSession;
