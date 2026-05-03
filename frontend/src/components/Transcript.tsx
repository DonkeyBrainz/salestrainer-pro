import React, { useEffect, useRef } from 'react';
import { Message } from '@/types';
import { AT } from '@/styles/tokens';

interface TranscriptProps {
  messages: Message[];
  currentInput?: string;
  readOnly?: boolean;
}

const Transcript: React.FC<TranscriptProps> = ({ messages, currentInput = '', readOnly = false }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentInput]);

  if (messages.length === 0 && !currentInput && !readOnly) {
    return (
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        opacity: 0.4, userSelect: 'none', pointerEvents: 'none',
      }}>
        <div style={{
          fontFamily: AT.mono, fontSize: 11,
          color: AT.inkMuted, letterSpacing: '0.14em', textTransform: 'uppercase',
          textAlign: 'center',
        }}>
          Your turn — speak naturally
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 40,
        background: `linear-gradient(to bottom, ${AT.bg}, transparent)`,
        zIndex: 2, pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: 40,
        background: `linear-gradient(to top, ${AT.bg}, transparent)`,
        zIndex: 2, pointerEvents: 'none',
      }} />

      <div
        ref={scrollRef}
        style={{
          flex: 1, overflowY: 'auto',
          padding: '32px 40px',
          display: 'flex', flexDirection: 'column', gap: 24,
        }}
      >
        {messages.map(msg => {
          const isCoach = msg.text.includes('[COACH MODE ACTIVE]');
          const displayText = msg.text
            .replace(/\[COACH MODE ACTIVE\]/g, '')
            .replace(/\[RESUMING SCENARIO\]/g, '')
            .trim();

          const isUser = msg.role === 'user';

          return (
            <div
              key={msg.id}
              className="animate-fade-in"
              style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start' }}
            >
              <div style={{
                fontFamily: AT.mono, fontSize: 9.5,
                letterSpacing: '0.16em', textTransform: 'uppercase',
                color: isCoach ? AT.butter : isUser ? AT.inkMuted : AT.terra,
                marginBottom: 6,
              }}>
                {isCoach ? 'Coach' : isUser ? 'You' : 'Guest'}
              </div>
              <div style={{
                maxWidth: '70%',
                fontFamily: AT.display,
                fontSize: 20, lineHeight: 1.45, fontWeight: 500,
                color: isUser ? AT.inkSoft : isCoach ? AT.butter : AT.ink,
                textAlign: isUser ? 'right' : 'left',
                padding: isCoach ? '12px 16px' : undefined,
                background: isCoach ? AT.butter + '14' : undefined,
                border: isCoach ? `1px solid ${AT.butter}33` : undefined,
                borderRadius: isCoach ? 10 : undefined,
              }}>
                {displayText}
              </div>
            </div>
          );
        })}

        {!readOnly && currentInput && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', opacity: 0.6 }}>
            <div style={{
              fontFamily: AT.mono, fontSize: 9.5,
              letterSpacing: '0.16em', textTransform: 'uppercase',
              color: AT.inkMuted, marginBottom: 6,
            }}>You</div>
            <div style={{
              maxWidth: '70%',
              fontFamily: AT.display, fontSize: 20, lineHeight: 1.45,
              fontStyle: 'italic', color: AT.inkMuted, textAlign: 'right',
            }}>
              {currentInput}
            </div>
          </div>
        )}

        <div style={{ height: 48, flexShrink: 0 }} />
      </div>
    </div>
  );
};

export default Transcript;
