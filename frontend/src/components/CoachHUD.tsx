import React, { useEffect, useState, useRef } from 'react';
import { X } from 'lucide-react';
import { CoachHint } from '@/types';
import { AT } from '@/styles/tokens';

interface CoachHUDProps {
  hint: CoachHint | null;
  onDismiss: () => void;
}

function HUDPanel({
  title,
  accent,
  flash,
  children,
}: {
  title: string;
  accent: string;
  flash?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div style={{
      background: 'rgba(22,29,24,0.92)',
      border: `1px solid ${AT.hair}`,
      borderTop: `2px solid ${accent}`,
      borderRadius: 10,
      padding: '12px 14px',
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <div
            className={flash ? 'pulse-dot' : ''}
            style={{
              width: 5, height: 5, borderRadius: '50%',
              background: accent,
              boxShadow: flash ? `0 0 10px ${accent}` : 'none',
            }}
          />
          <div style={{
            fontFamily: AT.mono, fontSize: 10,
            letterSpacing: '0.18em', color: accent,
            fontWeight: 600, textTransform: 'uppercase',
          }}>
            {title}
          </div>
        </div>
        <div style={{ fontFamily: AT.mono, fontSize: 9, color: AT.inkMuted, letterSpacing: '0.1em' }}>live</div>
      </div>
      {children}
    </div>
  );
}

const CoachHUD: React.FC<CoachHUDProps> = ({ hint, onDismiss }) => {
  const [isVisible, setIsVisible] = useState(false);
  const autoDismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (hint) {
      setIsVisible(true);
      if (autoDismissTimerRef.current) clearTimeout(autoDismissTimerRef.current);
      autoDismissTimerRef.current = setTimeout(() => {
        setIsVisible(false);
        setTimeout(() => onDismiss(), 200);
      }, 12000);
    } else {
      setIsVisible(false);
    }
    return () => {
      if (autoDismissTimerRef.current) clearTimeout(autoDismissTimerRef.current);
    };
  }, [hint, onDismiss]);

  if (!hint) return null;

  return (
    <div
      className={isVisible ? 'slide-in-right' : ''}
      style={{
        position: 'absolute',
        top: 24,
        right: 24,
        width: 280,
        opacity: isVisible ? 1 : 0,
        transition: 'opacity 0.2s',
        pointerEvents: isVisible ? 'auto' : 'none',
        zIndex: 20,
      }}
    >
      <HUDPanel title="Coach tip" accent={AT.sage} flash>
        <button
          onClick={() => { setIsVisible(false); setTimeout(() => onDismiss(), 200); }}
          style={{
            position: 'absolute', top: 10, right: 10,
            background: 'none', border: 'none',
            color: AT.inkMuted, cursor: 'pointer',
            padding: 2,
          }}
        >
          <X size={12} />
        </button>

        <div style={{ fontSize: 13.5, lineHeight: 1.45, color: AT.ink, marginTop: 8 }}>
          {hint.example_phrase ? (
            <>
              {hint.hint}{' '}
              <span style={{ color: AT.sage, fontStyle: 'italic' }}>Try: &ldquo;{hint.example_phrase}&rdquo;</span>
            </>
          ) : (
            hint.hint
          )}
        </div>

        {hint.ready_for_next_stage && (
          <div style={{
            marginTop: 8,
            fontFamily: AT.mono, fontSize: 10,
            color: AT.sage, letterSpacing: '0.1em', textTransform: 'uppercase',
          }}>
            ✓ Ready for next stage
          </div>
        )}

        <div style={{ marginTop: 6, fontFamily: AT.mono, fontSize: 9.5, color: AT.inkMuted, letterSpacing: '0.1em' }}>
          {hint.stage} stage
        </div>
      </HUDPanel>
    </div>
  );
};

export default CoachHUD;
export { HUDPanel };
