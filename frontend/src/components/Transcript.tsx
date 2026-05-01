import React, { useEffect, useRef } from 'react';
import { Message } from '@/types';
import { Sparkles, UserCheck, MessageSquare } from 'lucide-react';

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
      <div className="flex-1 flex items-center justify-center opacity-30 select-none pointer-events-none">
          <div className="flex flex-col items-center gap-4">
              <MessageSquare className="w-16 h-16 text-stone-300" />
              <p className="font-serif-display text-2xl text-stone-400">Transcript will appear here...</p>
          </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col relative">
      <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-[#F9F8F6] to-transparent z-10 pointer-events-none" />
      <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-[#F9F8F6] to-transparent z-10 pointer-events-none" />

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-12 flex flex-col gap-8 scroll-smooth custom-scrollbar"
      >
        {messages.map((msg) => {
          const isCoach = msg.text.includes('[COACH MODE ACTIVE]');
          const isResuming = msg.text.includes('[RESUMING SCENARIO]');

          let speakerName = 'Guest';
          if (msg.role === 'user') speakerName = 'You';
          if (isCoach) speakerName = 'Coach Intervention';

          const displayText = msg.text
            .replace(/\[COACH MODE ACTIVE\]/g, '')
            .replace(/\[RESUMING SCENARIO\]/g, '')
            .trim();

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}
            >
              <div className="flex items-center gap-1.5 mb-2 ml-1">
                {isCoach && <Sparkles className="w-3.5 h-3.5 text-amber-600" />}
                {isResuming && !isCoach && <UserCheck className="w-3.5 h-3.5 text-stone-400" />}
                <span className={`text-[10px] uppercase font-bold tracking-[0.15em] ${isCoach ? 'text-amber-600' : 'text-stone-400'}`}>
                  {speakerName}
                </span>
              </div>
              <div
                className={`
                  max-w-[85%] font-serif-display text-xl leading-relaxed
                  ${msg.role === 'user'
                    ? 'text-stone-500 text-right'
                    : isCoach
                        ? 'text-amber-900 text-left bg-amber-50 p-6 rounded-3xl border border-amber-200 shadow-sm'
                        : 'text-stone-800 text-left'
                  }
                `}
              >
                {displayText}
              </div>
            </div>
          );
        })}

        {!readOnly && currentInput && (
          <div className="flex flex-col items-end animate-pulse opacity-60">
            <span className="text-[10px] uppercase font-bold tracking-widest text-stone-400 mb-2 ml-1">You</span>
            <p className="max-w-[85%] font-serif-display text-xl leading-relaxed text-stone-400 text-right italic">
              {currentInput}
            </p>
          </div>
        )}

        <div className="h-24 shrink-0" />
      </div>
    </div>
  );
};

export default Transcript;
