import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { Persona, Difficulty } from '@/types';
import { fetchPersonas } from '@/services/personaService';
import { sessionService } from '@/services/sessionService';
import { useAuth } from '@/contexts/AuthContext';
import { VT, TIER_COLOR, TIER_LABEL, TIER_PIPS } from '@/styles/voiceprint';
import { NavTag, Cta, Scribble } from '@/components/voiceprint/primitives';
import MiniPlan, { sketchForPersona } from '@/components/voiceprint/MiniPlan';

interface PersonaSelectorProps {
  onSelect: (persona: Persona) => void;
  onCancel: () => void;
}

const DIFFICULTY_ORDER: Difficulty[] = ['high_regard', 'medium_regard', 'low_regard', 'no_regard'];

/** Backstories are one authored paragraph; split into a short two-line meta the way the mockup's hand-written copy reads. */
function splitBackstory(backstory: string): [string, string] {
  const sentences = backstory.split(/(?<=[.!?])\s+/).filter(Boolean);
  const first = sentences[0]?.trim() ?? backstory;
  const second = sentences[1]?.trim() ?? '';
  return [first, second];
}

function DraftCard({
  persona, difficulty, index, best, onClick,
}: {
  persona: Persona;
  difficulty: Difficulty;
  index: number;
  best: number | null;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const color = TIER_COLOR[difficulty] ?? VT.standard;
  const pips = TIER_PIPS[difficulty] ?? 2;
  const rotations = ['rotate(-1deg)', 'rotate(0.7deg) translateY(3px)', 'rotate(-0.4deg) translateY(-2px)'];
  const rotate = rotations[index % 3];
  const [role, line] = splitBackstory(persona.backstory);
  const sketch = sketchForPersona(persona.name, difficulty);

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flexShrink: 0, width: 196, cursor: 'pointer', position: 'relative',
        border: `7px solid ${color}`, background: 'rgba(6,20,40,0.72)',
        boxShadow: hovered
          ? '0 0 0 1px rgba(0,0,0,0.45), 0 16px 30px rgba(0,0,0,0.5), 0 0 22px rgba(255,255,255,0.12)'
          : '0 0 0 1px rgba(0,0,0,0.45), 0 10px 24px rgba(0,0,0,0.4)',
        padding: '14px 12px 12px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
        transform: hovered ? 'translateY(-6px)' : rotate,
        transition: 'transform .18s ease, box-shadow .18s ease',
      }}
    >
      <div style={{
        position: 'absolute', top: -21, left: '50%', transform: 'translateX(-50%) rotate(-2deg)',
        fontFamily: VT.oswald, fontWeight: 600, fontSize: 9.5, letterSpacing: '0.12em', textTransform: 'uppercase',
        padding: '3px 10px', color: '#101820', whiteSpace: 'nowrap', background: color,
      }}>
        {TIER_LABEL[difficulty]}
      </div>
      <div style={{
        fontFamily: VT.anton, fontSize: 24, letterSpacing: '0.04em', color: VT.line,
        textShadow: '0 2px 0 rgba(0,0,0,0.65), 0 0 14px rgba(0,0,0,0.5)', textTransform: 'uppercase', textAlign: 'center',
      }}>
        {persona.name ?? '?'}
      </div>
      <MiniPlan sketch={sketch} />
      <div style={{ fontSize: 9.5, letterSpacing: '0.06em', color: VT.textMuted, textAlign: 'center', lineHeight: 1.5 }}>
        {role}
        {line && <><br />{line}</>}
      </div>
      <div style={{
        width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderTop: `1px solid ${VT.lineFaint}`, paddingTop: 8, marginTop: 'auto',
      }}>
        <span style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: VT.textMuted }}>
          {best != null ? <>Best <b style={{ color: VT.text, fontFamily: VT.oswald, fontSize: 12 }}>{best}</b></> : <b style={{ opacity: 0.6 }}>NEW</b>}
        </span>
        <span style={{ display: 'flex', gap: 3 }}>
          {[0, 1, 2].map((i) => (
            <i key={i} style={{ width: 4, height: 10, display: 'inline-block', background: i < pips ? color : VT.lineFaint }} />
          ))}
        </span>
      </div>
    </div>
  );
}

const PersonaSelector: React.FC<PersonaSelectorProps> = ({ onSelect, onCancel }) => {
  const { accessToken } = useAuth();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [bestByPersonaId, setBestByPersonaId] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await fetchPersonas();
        setPersonas(data);
      } catch {
        setError('Failed to load customer scenarios');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    sessionService.listSessions(accessToken, { limit: 100 })
      .then((res) => {
        if (cancelled) return;
        const best: Record<string, number> = {};
        for (const s of res.sessions) {
          if (s.selectedPersona && s.score != null) {
            best[s.selectedPersona] = Math.max(best[s.selectedPersona] ?? 0, Math.round(s.score));
          }
        }
        setBestByPersonaId(best);
      })
      .catch(() => { /* best-score badges degrade to NEW */ });
    return () => { cancelled = true; };
  }, [accessToken]);

  const grouped: Record<Difficulty, Persona[]> = useMemo(() => ({
    high_regard: personas.filter(p => p.difficulty === 'high_regard'),
    medium_regard: personas.filter(p => p.difficulty === 'medium_regard'),
    low_regard: personas.filter(p => p.difficulty === 'low_regard'),
    no_regard: personas.filter(p => p.difficulty === 'no_regard'),
  }), [personas]);

  const ordered = DIFFICULTY_ORDER.flatMap((d) => grouped[d].map((p) => ({ persona: p, difficulty: d })));

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <Loader2 style={{ width: 32, height: 32, color: VT.amber, margin: '0 auto 16px', animation: 'spin 1s linear infinite' }} />
          <p style={{ fontFamily: VT.mono, fontSize: 12, color: VT.textMuted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Loading scenarios...
          </p>
        </div>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <AlertCircle style={{ width: 48, height: 48, color: VT.hard, margin: '0 auto 16px' }} />
          <h3 style={{ fontFamily: VT.anton, fontSize: 22, color: VT.text, marginBottom: 8 }}>Unable to load scenarios</h3>
          <p style={{ color: VT.textMuted, fontSize: 14, marginBottom: 24 }}>{error}</p>
          <Cta variant="ghost" onClick={onCancel}>Go back</Cta>
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '32px 40px 26px', minHeight: 0 }}>
      <style>{`
        @media (max-width: 720px) {
          .draft-row { flex-direction: column !important; overflow-x: visible !important; overflow-y: auto !important; align-items: center !important; }
        }
      `}</style>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <NavTag lobby onClick={onCancel}>◂ Lobby</NavTag>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, marginTop: 8 }}>
        <div style={{ fontFamily: VT.oswald, fontWeight: 600, letterSpacing: '0.28em', textTransform: 'uppercase', fontSize: 14, color: VT.text }}>
          Select a customer to draft
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, width: 'min(760px,80%)', color: VT.lineDim }}>
          <div style={{ flex: 1, height: 1, background: VT.lineDim }} />
          <span style={{ fontSize: 9, letterSpacing: '0.1em', color: VT.textMuted }}>{ordered.length} AVAILABLE</span>
          <div style={{ flex: 1, height: 1, background: VT.lineDim }} />
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', minHeight: 0 }}>
        <div className="draft-row" style={{ display: 'flex', gap: 22, overflowX: 'auto', padding: '26px 10px 30px', width: '100%', alignItems: 'stretch' }}>
          {ordered.map(({ persona, difficulty }, i) => (
            <DraftCard
              key={persona.id}
              persona={persona}
              difficulty={difficulty}
              index={i}
              best={bestByPersonaId[persona.id] ?? null}
              onClick={() => onSelect(persona)}
            />
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <Scribble>green = high regard · blue = medium · red = low… the biggest growth lives in red</Scribble>
      </div>
    </div>
  );
};

export default PersonaSelector;
