import React, { useEffect, useState, useRef } from 'react';
import { X, Info, Lightbulb, AlertTriangle, AlertOctagon, Target, ArrowRight } from 'lucide-react';
import { CoachHint } from '@/types';

interface CoachHUDProps {
  hint: CoachHint | null;
  onDismiss: () => void;
}

const CoachHUD: React.FC<CoachHUDProps> = ({ hint, onDismiss }) => {
  const [isVisible, setIsVisible] = useState(false);
  const autoDismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Show/hide with animation
  useEffect(() => {
    if (hint) {
      setIsVisible(true);

      // Clear existing timer
      if (autoDismissTimerRef.current) {
        clearTimeout(autoDismissTimerRef.current);
      }

      // Set new auto-dismiss timer (15 seconds)
      autoDismissTimerRef.current = setTimeout(() => {
        setIsVisible(false);
        setTimeout(() => onDismiss(), 300); // Wait for fade-out animation
      }, 15000);
    } else {
      setIsVisible(false);
    }

    return () => {
      if (autoDismissTimerRef.current) {
        clearTimeout(autoDismissTimerRef.current);
      }
    };
  }, [hint, onDismiss]);

  if (!hint) {
    return null;
  }

  // Get color scheme by intervention level
  const colorSchemes = {
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      text: 'text-blue-800',
      icon: Info,
    },
    suggestion: {
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      text: 'text-emerald-800',
      icon: Lightbulb,
    },
    warning: {
      bg: 'bg-amber-50',
      border: 'border-amber-300',
      text: 'text-amber-900',
      icon: AlertTriangle,
    },
    critical: {
      bg: 'bg-red-50',
      border: 'border-red-300',
      text: 'text-red-900',
      icon: AlertOctagon,
    },
    none: {
      bg: 'bg-stone-50',
      border: 'border-stone-200',
      text: 'text-stone-700',
      icon: Info,
    },
  };

  const scheme = colorSchemes[hint.level];
  const IconComponent = scheme.icon;

  return (
    <div
      className={`
        absolute top-20 right-6 w-80 transition-all duration-500 z-50
        ${isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'}
      `}
    >
      <div className={`${scheme.bg} ${scheme.border} border rounded-lg shadow-xl backdrop-blur-md bg-opacity-90 overflow-hidden`}>
        {/* Header */}
        <div className={`px-4 py-3 flex items-center justify-between border-b ${scheme.border}`}>
          <div className="flex items-center gap-2">
            <Target className={`w-4 h-4 ${scheme.text}`} />
            <span className={`text-xs font-bold uppercase tracking-widest ${scheme.text}`}>
              {hint.stage} Stage
            </span>
          </div>
          <button
            onClick={() => {
              setIsVisible(false);
              setTimeout(() => onDismiss(), 300);
            }}
            className={`p-1 rounded hover:bg-white/50 transition-colors ${scheme.text}`}
            title="Dismiss hint"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Hint Content */}
        <div className={`px-4 py-3 ${hint.example_phrase || hint.ready_for_next_stage ? 'border-b border-inherit' : ''}`}>
          <div className="flex items-start gap-3">
            <IconComponent className={`w-5 h-5 ${scheme.text} flex-shrink-0 mt-0.5`} />
            <p className={`text-sm ${scheme.text} leading-relaxed`}>
              {hint.hint}
            </p>
          </div>
        </div>

        {/* Example Phrase */}
        {hint.example_phrase && (
          <div className={`px-4 py-3 ${hint.ready_for_next_stage ? 'border-b border-inherit' : ''}`}>
            <p className={`text-xs font-bold uppercase tracking-widest ${scheme.text} mb-1.5`}>
              Try saying
            </p>
            <p className={`text-sm ${scheme.text} italic bg-white/50 rounded px-3 py-2 leading-relaxed`}>
              &ldquo;{hint.example_phrase}&rdquo;
            </p>
          </div>
        )}

        {/* Ready for Next Stage */}
        {hint.ready_for_next_stage && (
          <div className="px-4 py-3">
            <div className="flex items-center gap-2">
              <ArrowRight className={`w-4 h-4 ${scheme.text} flex-shrink-0`} />
              <p className={`text-xs font-bold uppercase tracking-widest ${scheme.text}`}>
                Ready for next stage
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CoachHUD;
