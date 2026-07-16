// Voiceprint design tokens — blueprint/architectural-drawing aesthetic.
// See design_handoff_voiceprint/README.md for the full spec this was lifted from.
export const VT = {
  blue: '#2058A6',
  blueDeep: '#123157',
  bluePanel: 'rgba(255,255,255,0.045)',
  bluePanelHover: 'rgba(255,255,255,0.09)',

  line: '#FFFFFF',
  lineDim: 'rgba(255,255,255,0.35)',
  lineFaint: 'rgba(255,255,255,0.10)',

  text: '#EFF5FF',
  textMuted: 'rgba(239,245,255,0.6)',

  amber: '#F0A24E',
  rapport: '#8FBF6B', // high regard
  standard: '#7EB0EE', // medium regard
  hard: '#E4574A', // low regard
  special: '#C79BEE',

  sticky: '#CFE6A8',
  stickyInk: '#2C3B1E',
  stickyBright: '#F5E6A8',

  anton: '"Anton", sans-serif',
  caveat: '"Caveat", cursive',
  oswald: '"Oswald", sans-serif',
  mono: '"IBM Plex Mono", ui-monospace, monospace',
} as const;

/** Score → tier color, per README: rapport >=80, amber >=65, else hard. */
export function scoreColor(v: number | null | undefined): string {
  if (v == null) return VT.textMuted;
  if (v >= 80) return VT.rapport;
  if (v >= 65) return VT.amber;
  return VT.hard;
}

/** Difficulty tier → accent color + label, shared across persona cards, tables, pips. */
export const TIER_COLOR: Record<string, string> = {
  high_regard: VT.rapport,
  medium_regard: VT.standard,
  low_regard: VT.hard,
  no_regard: VT.hard,
};

export const TIER_LABEL: Record<string, string> = {
  high_regard: 'High regard',
  medium_regard: 'Medium regard',
  low_regard: 'Low regard',
  no_regard: 'No regard',
};

export const TIER_PIPS: Record<string, number> = {
  high_regard: 1,
  medium_regard: 2,
  low_regard: 3,
  no_regard: 3,
};
