import React from 'react';
import type { Difficulty } from '@/types';

// Hand-drawn 120×80 architectural sketches, one per named persona in the
// Voiceprint mockup. Kept as a fixed pool (see design_handoff_voiceprint) and
// mapped deterministically onto whatever personas the API returns.
const NAMED_SKETCHES: Record<string, React.ReactNode> = {
  // Marcus · contractor: gut renovation — hatched demo zone, sawhorse, missing wall
  Marcus: (
    <>
      <path d="M 8 8 h 104 v 64 h -60 M 32 72 h -24 z" />
      <path d="M 40 72 l 8 0" strokeDasharray="2 3" />
      <path d="M 70 20 l 34 28 M 78 20 l 26 22 M 86 20 l 18 15" opacity="0.5" />
      <path d="M 20 52 l 8 -12 l 8 12 M 24 52 v 8 M 32 52 v 8" />
      <rect x="14" y="16" width="22" height="10" />
    </>
  ),
  // Jennifer · first-time buyer: tiny starter home — bed, half-kitchen, one door
  Jennifer: (
    <>
      <rect x="20" y="8" width="80" height="64" />
      <path d="M 20 44 h 34 M 62 44 h 38" />
      <rect x="26" y="14" width="20" height="26" />
      <path d="M 26 22 h 20" />
      <rect x="76" y="52" width="18" height="8" />
      <path d="M 54 44 a 8 8 0 0 1 8 8" strokeDasharray="2 2" />
    </>
  ),
  // Amanda · relocating w/ kids: three small bedrooms off a hall
  Amanda: (
    <>
      <rect x="8" y="8" width="104" height="64" />
      <path d="M 8 32 h 104 M 42 32 v 40 M 76 32 v 40" />
      <rect x="14" y="40" width="14" height="18" />
      <rect x="48" y="40" width="14" height="18" />
      <rect x="82" y="40" width="14" height="18" />
      <circle cx="60" cy="20" r="7" />
    </>
  ),
  // Alex · urban SWE: open studio loft — island counter, desk, bike by the door
  Alex: (
    <>
      <path d="M 8 24 l 20 -16 h 84 v 64 h -104 z" />
      <rect x="44" y="34" width="32" height="9" />
      <rect x="90" y="14" width="16" height="22" />
      <circle cx="20" cy="58" r="6" />
      <circle cx="34" cy="58" r="6" />
      <path d="M 20 58 l 7 -10 l 7 10" />
    </>
  ),
  // Thomas · hobby-farm curious: cabin + wraparound porch + field rows
  Thomas: (
    <>
      <rect x="26" y="18" width="56" height="44" />
      <path d="M 16 10 h 76 v 60 h -76 z" strokeDasharray="3 3" />
      <rect x="34" y="26" width="16" height="12" />
      <path d="M 96 16 v 56 M 102 16 v 56 M 108 16 v 56" opacity="0.55" />
    </>
  ),
  // Diane · downsizing: big old footprint (ghost) with a small unit inside
  Diane: (
    <>
      <rect x="8" y="8" width="104" height="64" strokeDasharray="3 3" opacity="0.45" />
      <rect x="58" y="30" width="46" height="36" />
      <rect x="64" y="38" width="14" height="16" />
      <circle cx="92" cy="48" r="6" />
      <path d="M 16 18 l 30 22 M 46 18 l -30 22" opacity="0.4" />
    </>
  ),
  // Ray · investor: mirrored duplex — two identical units, unit numbers
  Ray: (
    <>
      <rect x="8" y="8" width="104" height="64" />
      <path d="M 60 8 v 64" strokeWidth="2" />
      <rect x="16" y="16" width="16" height="12" />
      <rect x="88" y="16" width="16" height="12" />
      <path d="M 16 56 h 28 M 76 56 h 28" />
      <path d="M 30 40 a 6 6 0 0 1 6 6 M 90 40 a 6 6 0 0 0 -6 6" strokeDasharray="2 2" />
    </>
  ),
};

const SKETCH_POOL = Object.keys(NAMED_SKETCHES);

// Fallback pool by tier, for personas that grow beyond the named 7.
const TIER_FALLBACK: Record<Difficulty, string[]> = {
  high_regard: ['Marcus'],
  medium_regard: ['Jennifer', 'Amanda', 'Alex', 'Thomas'],
  low_regard: ['Diane', 'Ray'],
  no_regard: ['Diane', 'Ray'],
};

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

/** Deterministically pick a sketch for a persona: exact name match first, then a stable hash within the difficulty tier's pool. */
export function sketchForPersona(name: string | undefined, difficulty: Difficulty): string {
  if (name && NAMED_SKETCHES[name]) return name;
  const pool = TIER_FALLBACK[difficulty] ?? SKETCH_POOL;
  const key = name ?? difficulty;
  return pool[hashString(key) % pool.length];
}

export default function MiniPlan({ sketch, style }: { sketch: string; style?: React.CSSProperties }) {
  const paths = NAMED_SKETCHES[sketch] ?? NAMED_SKETCHES[SKETCH_POOL[0]];
  return (
    <svg
      viewBox="0 0 120 80"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      stroke="rgba(255,255,255,0.55)"
      strokeWidth="1.3"
      style={{ width: '100%', opacity: 0.9, ...style }}
    >
      {paths}
    </svg>
  );
}
