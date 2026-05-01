import React, { useEffect, useState, useRef } from 'react';
import { Mic, MicOff, Settings, XCircle, Lightbulb, RotateCcw, ClipboardCheck, Coffee, Play, Power, Loader2 } from 'lucide-react';
import { ConnectionState, AppMode } from '@/types';

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

        const updateMicLevel = () => {
            inputAnalyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) { sum += dataArray[i]; }
            const average = sum / bufferLength;
            const level = Math.min(average / 40, 1.0);
            setMicVolume(level);
            rafRef.current = requestAnimationFrame(updateMicLevel);
        };
        updateMicLevel();
    } else {
        setMicVolume(0);
    }
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [isConnected, inputAnalyser]);

  const ringScale = 1 + (micVolume * 0.6);
  const ringOpacity = 0.2 + (micVolume * 0.5);

  return (
    <div className="flex flex-col items-center gap-2 z-10 w-full max-w-xl relative px-4">
      <div className="flex items-center justify-center gap-6 w-full">

        {/* Left: Hint button (only in Training mode) */}
        {isTrainingMode && (
          <div className="relative group shrink-0">
              <button
                onClick={onHint}
                disabled={!isConnected || isGeneratingHint}
                className={`
                  flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300
                  ${isConnected
                    ? 'bg-[#8B5E3C] text-white shadow-md hover:bg-[#724C31]'
                    : 'bg-stone-200 text-stone-400 cursor-not-allowed opacity-50'
                  }
                `}
                title="Get AI Hint"
              >
                <Lightbulb className={`w-4 h-4 ${isGeneratingHint ? 'animate-pulse' : ''}`} fill={isConnected ? "currentColor" : "none"} />
              </button>
              {isConnected && (
                  <div className="absolute -bottom-1 -right-1 bg-emerald-500 text-white p-1 rounded-full border-2 border-white shadow-sm" title="Real-time Coaching Active">
                      <Coffee className="w-2.5 h-2.5" />
                  </div>
              )}
          </div>
        )}

        {/* Center-Left: Mute/Unmute Toggle (Separated from Connection) */}
        <div className="relative shrink-0">
            <button
              onClick={onToggleMute}
              disabled={!isConnected}
              className={`
                relative flex items-center justify-center w-12 h-12 rounded-full transition-all duration-300 shadow-sm
                ${!isConnected
                    ? 'bg-stone-100 text-stone-300 cursor-not-allowed'
                    : isMuted
                        ? 'bg-red-50 text-red-500 border border-red-100 hover:bg-red-100'
                        : 'bg-emerald-50 text-emerald-600 border border-emerald-100 hover:bg-emerald-100'
                }
              `}
              title={isMuted ? "Unmute Mic" : "Mute Mic"}
            >
              {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              {!isMuted && isConnected && (
                <div
                    className="absolute inset-0 rounded-full bg-emerald-500 transition-transform duration-75 ease-out pointer-events-none -z-10"
                    style={{
                        transform: `scale(${ringScale})`,
                        opacity: ringOpacity * 0.4
                    }}
                />
              )}
            </button>
            {isConnected && (
              <span className="absolute -top-8 left-1/2 -translate-x-1/2 text-[9px] font-bold uppercase tracking-widest text-stone-400 whitespace-nowrap">
                {isMuted ? 'Mic Muted' : 'Mic Live'}
              </span>
            )}
        </div>

        {/* Center: Connect/Disconnect Primary Action */}
        <div className="flex items-center justify-center min-w-[200px]">
            <button
              onClick={onToggleConnect}
              disabled={isConnecting}
              className={`
                group flex items-center justify-center gap-3 px-8 h-14 rounded-full transition-all duration-500 ease-out shadow-xl font-bold uppercase tracking-widest text-sm
                ${isConnected
                  ? 'bg-red-900 text-white hover:bg-red-800'
                  : 'bg-[#2C2825] text-[#F9F8F6] hover:bg-black hover:scale-105 active:scale-95'
                }
                ${isConnecting ? 'opacity-80 cursor-wait animate-pulse' : ''}
              `}
            >
              {isConnecting ? (
                <div className="w-5 h-5 border-2 border-stone-400 border-t-transparent rounded-full animate-spin" />
              ) : isConnected ? (
                <><Power className="w-5 h-5" /> End Session</>
              ) : (
                <><Play className="w-5 h-5 fill-current" /> Start Practice</>
              )}
            </button>
        </div>

        {/* Right: Restart or Action */}
        <div className="shrink-0 min-w-[40px] flex justify-end">
             {onEvaluate && isConnected ? (
                <button
                  onClick={onEvaluate}
                  disabled={isEvaluating}
                  className={`
                    flex items-center justify-center gap-2 px-6 h-12 rounded-full text-xs font-bold uppercase tracking-wider transition-all shadow-md
                    ${isEvaluating
                      ? 'bg-emerald-500 text-white cursor-wait opacity-80'
                      : 'bg-emerald-600 text-white hover:bg-emerald-700 active:scale-95'
                    }
                  `}
                >
                    {isEvaluating ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Grading...
                      </>
                    ) : (
                      <>
                        <ClipboardCheck className="w-4 h-4" />
                        Evaluate
                      </>
                    )}
                </button>
            ) : (
                <button
                  onClick={onRestart}
                  disabled={!isConnected}
                  className={`
                    flex items-center justify-center w-10 h-10 rounded-full transition-all
                    ${isConnected
                      ? 'bg-stone-200 text-stone-600 hover:bg-stone-300'
                      : 'bg-stone-100 text-stone-300 cursor-not-allowed'
                    }
                  `}
                  title="Restart Session"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
            )}
        </div>
      </div>

      {/* Connection Status Label */}
      <div className="text-[10px] uppercase tracking-widest font-bold text-stone-400 mt-2">
        {isConnected ? 'Session Connected' : isConnecting ? 'Establishing Link...' : 'Waiting to begin'}
      </div>
    </div>
  );
};

export default ControlBar;
