import React, { useEffect, useState, useRef } from 'react';
import { Mic, MicOff, RotateCcw, Lightbulb, ClipboardCheck, Play, Power, Settings, Loader2 } from 'lucide-react';
import { ConnectionState, AppMode } from '@/types';
import { AT } from '@/styles/tokens';

interface ControlBarProps {
  connectionState: ConnectionState;
  isMuted: boolean;
  onToggleConnect: () => void;
  onToggleMute: () => void;
  onRestart: () => void;
  onHint: () => void;
  onEvaluate?: () => void;
  isEvaluating?: boolean;
  isGeneratingHint: boolean;
  inputAnalyser: AnalyserNode | null;
  mode?: AppMode;
}

function CircleBtn({
  onClick,
  disabled,
  title,
  children,
  active,
}: {
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  children: React.ReactNode;
  active?: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: 44, height: 44, borderRadius: 10,
        background: hovered && !disabled ? AT.surface : AT.surface2,
        border: `1px solid ${active ? AT.terra + '60' : AT.hair}`,
        color: disabled ? AT.inkMuted : AT.inkSoft,
        fontSize: 16, cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'grid', placeItems: 'center',
        opacity: disabled ? 0.4 : 1,
        transition: 'background 0.15s',
      }}
    >
      {children}
    </button>
  );
}

const ControlBar: React.FC<ControlBarProps> = ({
  connectionState,
  isMuted,
  onToggleConnect,
  onToggleMute,
  onRestart,
  onHint,
  onEvaluate,
  isEvaluating = false,
  isGeneratingHint,
  inputAnalyser,
  mode,
}) => {
  const isConnected = connectionState === ConnectionState.CONNECTED;
  const isConnecting = connectionState === ConnectionState.CONNECTING;
  const isTrainingMode = mode === AppMode.TRAINING;

  const [micVolume, setMicVolume] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (isConnected && inputAnalyser) {
      const bufferLength = inputAnalyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      const tick = () => {
        inputAnalyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) sum += dataArray[i];
        setMicVolume(Math.min(sum / bufferLength / 40, 1));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } else {
      setMicVolume(0);
    }
    return () => { if (rafRef.current !== null) cancelAnimationFrame(rafRef.current); };
  }, [isConnected, inputAnalyser]);

  const ringScale = 1 + micVolume * 0.5;
  const ringOpacity = 0.15 + micVolume * 0.4;

  return (
    <div style={{
      height: 76,
      borderTop: `1px solid ${AT.hair}`,
      background: AT.surface,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      gap: 12,
      flexShrink: 0,
    }}>
      {/* Hint */}
      {isTrainingMode ? (
        <CircleBtn
          onClick={onHint}
          disabled={!isConnected || isGeneratingHint}
          title="Coach hint"
        >
          <Lightbulb size={16} style={{ color: isConnected ? AT.sage : AT.inkMuted }} />
        </CircleBtn>
      ) : (
        <div style={{ width: 44 }} />
      )}

      {/* Mic */}
      <div style={{ position: 'relative' }}>
        {!isMuted && isConnected && (
          <div style={{
            position: 'absolute', inset: 0, borderRadius: 10,
            background: AT.sage,
            transform: `scale(${ringScale})`,
            opacity: ringOpacity,
            pointerEvents: 'none',
            transition: 'transform 0.08s, opacity 0.08s',
          }} />
        )}
        <CircleBtn
          onClick={onToggleMute}
          disabled={!isConnected}
          title={isMuted ? 'Unmute' : 'Mute'}
          active={isConnected && !isMuted}
        >
          {isMuted
            ? <MicOff size={16} style={{ color: AT.terra }} />
            : <Mic size={16} style={{ color: isConnected ? AT.sage : AT.inkMuted }} />
          }
        </CircleBtn>
      </div>

      {/* Primary CTA */}
      <button
        onClick={onToggleConnect}
        disabled={isConnecting}
        style={{
          padding: '14px 30px',
          borderRadius: 10,
          background: isConnected ? AT.terraDim : AT.terra,
          color: isConnected ? AT.terra : AT.bg,
          border: isConnected ? `1px solid ${AT.terra}40` : 'none',
          fontSize: 14, fontWeight: 600,
          fontFamily: AT.sans,
          cursor: isConnecting ? 'wait' : 'pointer',
          display: 'inline-flex', alignItems: 'center', gap: 10,
          boxShadow: isConnected ? 'none' : `0 0 24px ${AT.terra}66`,
          opacity: isConnecting ? 0.7 : 1,
          transition: 'background 0.2s, box-shadow 0.2s',
          minWidth: 160,
          justifyContent: 'center',
        }}
      >
        {isConnecting ? (
          <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Connecting…</>
        ) : isConnected ? (
          <><Power size={16} /> End Session</>
        ) : (
          <><Play size={16} style={{ fill: AT.bg }} /> Start Practice</>
        )}
      </button>

      {/* Restart or Evaluate */}
      {onEvaluate && isConnected ? (
        <button
          onClick={onEvaluate}
          disabled={isEvaluating}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 16px', borderRadius: 8,
            background: AT.sage + '22',
            border: `1px solid ${AT.sageDim}`,
            color: AT.sage,
            fontFamily: AT.mono, fontSize: 11,
            letterSpacing: '0.1em', textTransform: 'uppercase',
            cursor: isEvaluating ? 'wait' : 'pointer',
            opacity: isEvaluating ? 0.6 : 1,
          }}
        >
          {isEvaluating
            ? <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Grading…</>
            : <><ClipboardCheck size={14} /> Evaluate</>
          }
        </button>
      ) : (
        <CircleBtn onClick={onRestart} disabled={!isConnected} title="Restart">
          <RotateCcw size={16} />
        </CircleBtn>
      )}

      {/* Settings */}
      <CircleBtn title="Settings">
        <Settings size={16} />
      </CircleBtn>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default ControlBar;
