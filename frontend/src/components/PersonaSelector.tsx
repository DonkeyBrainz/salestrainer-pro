import React, { useEffect, useState } from 'react';
import { Persona, Difficulty } from '@/types';
import { fetchPersonas } from '@/services/personaService';
import { Loader2, AlertCircle } from 'lucide-react';
import { AT } from '@/styles/tokens';

interface PersonaSelectorProps {
  onSelect: (persona: Persona) => void;
  onCancel: () => void;
}

const TIER_CONFIG: Record<Difficulty, {
  code: string;
  label: string;
  sub: string;
  color: string;
  pips: number;
}> = {
  high_regard: {
    code: 'EASY',
    label: 'High regard',
    sub: 'Friendlier reception. Build confidence and momentum.',
    color: AT.sage,
    pips: 1,
  },
  medium_regard: {
    code: 'STANDARD',
    label: 'Medium regard',
    sub: 'Real-world default. Earned trust gets results.',
    color: AT.butter,
    pips: 2,
  },
  low_regard: {
    code: 'HARD',
    label: 'Low regard',
    sub: 'Skeptical, tested, hard-won. The biggest growth lives here.',
    color: AT.terra,
    pips: 3,
  },
  no_regard: {
    code: 'LOCKED',
    label: 'No regard',
    sub: 'Maximum difficulty.',
    color: AT.inkMuted,
    pips: 3,
  },
};

const DIFFICULTY_ORDER: Difficulty[] = ['high_regard', 'medium_regard', 'low_regard', 'no_regard'];

function TierHeader({ difficulty, count }: { difficulty: Difficulty; count: number }) {
  const cfg = TIER_CONFIG[difficulty];
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      padding: '14px 18px',
      borderRadius: 12,
      background: cfg.color + '0e',
      border: `1px solid ${cfg.color}33`,
      marginBottom: 12,
    }}>
      <div style={{ fontFamily: AT.display, fontSize: 20, fontWeight: 700, color: cfg.color, letterSpacing: '0.04em' }}>{cfg.code}</div>
      <div style={{ width: 1, height: 24, background: AT.hair }} />
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.ink, letterSpacing: '0.16em', textTransform: 'uppercase' }}>{cfg.label}</div>
        <div style={{ fontSize: 12, color: AT.inkSoft, marginTop: 2 }}>{cfg.sub}</div>
      </div>
      <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted, letterSpacing: '0.12em' }}>
        {count} scenario{count !== 1 ? 's' : ''}
      </div>
    </div>
  );
}

function PersonaCard({ persona, difficulty, onClick }: { persona: Persona; difficulty: Difficulty; onClick: () => void }) {
  const [hovered, setHovered] = useState(false);
  const cfg = TIER_CONFIG[difficulty];
  const hideDetails = difficulty === 'low_regard' || difficulty === 'no_regard' || !persona.name;

  const initial = persona.name ? persona.name[0] : '?';

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: AT.surface,
        border: `1px solid ${hovered ? cfg.color + '66' : AT.hair}`,
        borderRadius: 12,
        padding: 16,
        cursor: 'pointer',
        minHeight: 168,
        display: 'flex',
        flexDirection: 'column',
        transition: 'border-color 0.15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8,
          background: cfg.color + '20', color: cfg.color,
          fontFamily: AT.display, fontSize: 16, fontWeight: 700,
          display: 'grid', placeItems: 'center',
        }}>
          {initial}
        </div>
        <div style={{ display: 'flex', gap: 3 }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{
              width: 5, height: 12, borderRadius: 1,
              background: i < cfg.pips ? cfg.color : AT.hair,
            }} />
          ))}
        </div>
      </div>

      {hideDetails ? (
        <div style={{ fontSize: 12.5, color: AT.inkSoft, lineHeight: 1.5, flex: 1 }}>{persona.backstory}</div>
      ) : (
        <>
          <div style={{ fontFamily: AT.display, fontSize: 18, fontWeight: 600, color: AT.ink }}>{persona.name}</div>
          <div style={{ fontFamily: AT.mono, fontSize: 10.5, color: AT.inkMuted, letterSpacing: '0.06em', marginTop: 2 }}>
            {persona.backstory.slice(0, 40)}&hellip;
          </div>
          <div style={{ marginTop: 10, fontSize: 12.5, color: AT.inkSoft, lineHeight: 1.5, flex: 1 }}>{persona.backstory}</div>
        </>
      )}

      <div style={{
        marginTop: 12,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        paddingTop: 10,
        borderTop: `1px solid ${AT.hair}`,
      }}>
        <div style={{ fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted, letterSpacing: '0.1em' }}>
          {cfg.label}
        </div>
        <div style={{ fontFamily: AT.mono, fontSize: 11, color: hovered ? cfg.color : AT.inkMuted, fontWeight: 600, transition: 'color 0.15s' }}>›</div>
      </div>
    </div>
  );
}

function FilterChip({ active, children, onClick }: { active?: boolean; children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '7px 12px',
        borderRadius: 8,
        background: active ? AT.surface2 : 'transparent',
        border: `1px solid ${active ? AT.hair : AT.hairSoft}`,
        color: active ? AT.ink : AT.inkSoft,
        fontSize: 12,
        fontFamily: AT.mono,
        letterSpacing: '0.08em',
        cursor: 'pointer',
        transition: 'background 0.15s, border-color 0.15s',
      }}
    >
      {children}
    </button>
  );
}

const PersonaSelector: React.FC<PersonaSelectorProps> = ({ onSelect, onCancel }) => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPersonas = async () => {
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
    loadPersonas();
  }, []);

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: AT.bg }}>
        <div style={{ textAlign: 'center' }}>
          <Loader2 style={{ width: 32, height: 32, color: AT.terra, margin: '0 auto 16px', animation: 'spin 1s linear infinite' }} />
          <p style={{ fontFamily: AT.mono, fontSize: 12, color: AT.inkMuted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Loading scenarios...
          </p>
        </div>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: AT.bg, padding: 24 }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <AlertCircle style={{ width: 48, height: 48, color: AT.terra, margin: '0 auto 16px' }} />
          <h3 style={{ fontFamily: AT.display, fontSize: 22, fontWeight: 600, color: AT.ink, marginBottom: 8 }}>
            Unable to Load Scenarios
          </h3>
          <p style={{ color: AT.inkSoft, fontSize: 14, marginBottom: 24 }}>{error}</p>
          <button
            onClick={onCancel}
            style={{
              padding: '10px 24px', borderRadius: 8,
              background: AT.surface2, color: AT.ink,
              border: `1px solid ${AT.hair}`,
              fontFamily: AT.mono, fontSize: 12,
              letterSpacing: '0.1em', cursor: 'pointer',
            }}
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const grouped: Record<Difficulty, Persona[]> = {
    high_regard:   personas.filter(p => p.difficulty === 'high_regard'),
    medium_regard: personas.filter(p => p.difficulty === 'medium_regard'),
    low_regard:    personas.filter(p => p.difficulty === 'low_regard'),
    no_regard:     personas.filter(p => p.difficulty === 'no_regard'),
  };

  return (
    <div style={{ flex: 1, overflow: 'auto', background: AT.bg, padding: '28px 40px 48px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <div style={{ fontFamily: AT.display, fontSize: 40, fontWeight: 600, letterSpacing: '-0.025em', lineHeight: 1, color: AT.ink }}>
            Pick your <span style={{ color: AT.terra, fontStyle: 'italic' }}>customer</span>
          </div>
          <div style={{ marginTop: 10, fontSize: 14, color: AT.inkSoft, maxWidth: 540 }}>
            Each persona has their own goals, objections, and a regard level — how warm they are toward your pitch.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <FilterChip active>All regards</FilterChip>
          <FilterChip>New only</FilterChip>
          <FilterChip>Unbeaten</FilterChip>
        </div>
      </div>

      {/* Tiers */}
      {DIFFICULTY_ORDER.map(difficulty => {
        const group = grouped[difficulty];
        if (group.length === 0) return null;
        return (
          <div key={difficulty} style={{ marginBottom: 28 }}>
            <TierHeader difficulty={difficulty} count={group.length} />
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
              gap: 10,
            }}>
              {group.map(persona => (
                <PersonaCard
                  key={persona.id}
                  persona={persona}
                  difficulty={difficulty}
                  onClick={() => onSelect(persona)}
                />
              ))}
            </div>
          </div>
        );
      })}

      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <button
          onClick={onCancel}
          style={{
            background: 'none', border: 'none',
            fontFamily: AT.mono, fontSize: 11,
            color: AT.inkMuted, letterSpacing: '0.12em',
            textTransform: 'uppercase', cursor: 'pointer',
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

export default PersonaSelector;
