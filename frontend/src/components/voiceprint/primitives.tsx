import React from 'react';
import { VT } from '@/styles/voiceprint';

// ── Panel ─────────────────────────────────────────────────────────────────────
export function Panel({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ background: VT.bluePanel, border: `1px solid ${VT.lineFaint}`, padding: '13px 15px', ...style }}>
      {children}
    </div>
  );
}

export function PanelTitle({ children, dot }: { children: React.ReactNode; dot: string }) {
  return (
    <div style={{
      fontSize: 9.5, letterSpacing: '0.16em', textTransform: 'uppercase', color: VT.textMuted,
      display: 'flex', alignItems: 'center', gap: 7, marginBottom: 9,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: 2, background: dot, display: 'inline-block', flexShrink: 0 }} />
      {children}
    </div>
  );
}

// ── Sticky note ───────────────────────────────────────────────────────────────
export function StickyNote({
  title, children, rotate = -4, width, bright, pulse, unwrap, style,
}: {
  title: string;
  children: React.ReactNode;
  rotate?: number;
  width?: number | string;
  bright?: boolean;
  pulse?: boolean;
  unwrap?: boolean;
  style?: React.CSSProperties;
}) {
  const className = [pulse && 'sticky-pulse', unwrap && 'sticky-unwrap'].filter(Boolean).join(' ') || undefined;
  return (
    <div
      className={className}
      style={{
        width: width ?? 190,
        background: bright ? VT.stickyBright : VT.sticky,
        color: VT.stickyInk,
        padding: '16px 16px 20px',
        fontFamily: VT.oswald,
        fontSize: 12,
        lineHeight: 1.5,
        transform: `rotate(${rotate}deg)`,
        boxShadow: '3px 4px 10px rgba(0,0,0,0.3)',
        clipPath: 'polygon(0 0,100% 0,100% 88%,88% 100%,0 100%)',
        ...({ '--rot': `${rotate}deg` } as React.CSSProperties),
        ...style,
      }}
    >
      <div style={{ fontWeight: 600, letterSpacing: '0.08em', fontSize: 11, textTransform: 'uppercase', marginBottom: 8, opacity: 0.75 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

// ── Nav tag (rotated back-nav) ───────────────────────────────────────────────
export function NavTag({ children, onClick, lobby }: { children: React.ReactNode; onClick: () => void; lobby?: boolean }) {
  const [hovered, setHovered] = React.useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        cursor: 'pointer',
        background: hovered ? '#1a4278' : VT.blueDeep,
        border: `1px solid ${VT.lineDim}`,
        color: VT.text,
        fontFamily: VT.oswald,
        fontWeight: 600,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        fontSize: 12,
        padding: '10px 18px',
        transform: `rotate(${lobby ? -2 : -3}deg) translateY(${hovered ? -2 : 0}px)`,
        boxShadow: '2px 3px 8px rgba(0,0,0,0.35)',
        transition: 'transform .2s ease, background .2s ease',
        display: 'inline-block',
        marginBottom: lobby ? 4 : 0,
        alignSelf: lobby ? 'flex-start' : undefined,
      }}
    >
      {children}
    </div>
  );
}

// ── CTA button ────────────────────────────────────────────────────────────────
type CtaVariant = 'default' | 'active' | 'ghost' | 'muted';

export function Cta({
  children, onClick, variant = 'default', disabled, style,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: CtaVariant;
  disabled?: boolean;
  style?: React.CSSProperties;
}) {
  const [hovered, setHovered] = React.useState(false);
  const base: React.CSSProperties = {
    background: 'transparent',
    border: `1px solid ${VT.line}`,
    color: VT.line,
    fontFamily: VT.mono,
    fontSize: 12,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    padding: '12px 26px',
    borderRadius: 1,
    cursor: disabled ? 'default' : 'pointer',
    transition: 'all .25s ease',
    whiteSpace: 'nowrap',
    opacity: disabled ? 0.4 : 1,
  };
  if (variant === 'active') {
    base.background = VT.amber;
    base.borderColor = VT.amber;
    base.color = '#1a1206';
  } else if (variant === 'ghost') {
    base.borderColor = VT.lineDim;
    base.color = VT.textMuted;
  } else if (variant === 'muted') {
    base.background = VT.hard;
    base.borderColor = VT.hard;
    base.color = '#1a0806';
  }
  if (hovered && !disabled && variant !== 'active' && variant !== 'muted') {
    base.background = 'rgba(255,255,255,0.08)';
  }
  return (
    <button
      onClick={disabled ? undefined : onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      disabled={disabled}
      style={{ ...base, ...style }}
    >
      {children}
    </button>
  );
}

// ── Frame label ("FIG. NN — …") ─────────────────────────────────────────────
export function FrameLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontFamily: VT.oswald, fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase',
      fontSize: 12.5, color: VT.textMuted, textAlign: 'center',
    }}>
      {children}
    </div>
  );
}

// ── Mode tag (practice / assess badge) ──────────────────────────────────────
export function ModeTag({ mode }: { mode: 'practice' | 'assess' }) {
  const isAssess = mode === 'assess';
  return (
    <span style={{
      fontFamily: VT.oswald, fontWeight: 600, fontSize: 8.5, letterSpacing: '0.1em', textTransform: 'uppercase',
      padding: '2px 7px', display: 'inline-block',
      background: isAssess ? 'rgba(199,155,238,0.16)' : 'rgba(126,176,238,0.18)',
      color: isAssess ? VT.special : VT.standard,
      border: `1px solid ${isAssess ? 'rgba(199,155,238,0.4)' : 'rgba(126,176,238,0.4)'}`,
    }}>
      {isAssess ? 'assess' : 'practice'}
    </span>
  );
}

// ── Scribble (Caveat handwriting) ────────────────────────────────────────────
export function Scribble({ children, color }: { children: React.ReactNode; color?: string }) {
  return (
    <div style={{ fontFamily: VT.caveat, fontSize: 22, color: color ?? VT.lineDim }}>
      {children}
    </div>
  );
}

// ── Blueprint table ───────────────────────────────────────────────────────────
export function BlueprintTable({ children }: { children: React.ReactNode }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5 }}>
      {children}
    </table>
  );
}

export const bpThStyle: React.CSSProperties = {
  fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted,
  fontWeight: 500, textAlign: 'left', padding: '0 8px 7px 0', borderBottom: `1px solid ${VT.lineDim}`,
};

export const bpTdStyle: React.CSSProperties = {
  padding: '9px 8px 9px 0', borderBottom: `1px dashed ${VT.lineFaint}`, verticalAlign: 'middle',
};

// ── KPI card ──────────────────────────────────────────────────────────────────
export function KpiCard({ label, value, sub, color }: { label: string; value: React.ReactNode; sub?: string; color?: string }) {
  return (
    <div style={{ flex: 1, minWidth: 140, background: VT.bluePanel, border: `1px solid ${VT.lineFaint}`, padding: '12px 14px' }}>
      <div style={{ fontSize: 8.5, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted }}>{label}</div>
      <div style={{ fontFamily: VT.anton, fontSize: 27, marginTop: 4, color: color ?? VT.text }}>{value}</div>
      {sub && <div style={{ fontSize: 9.5, color: VT.textMuted, marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

// ── Grade cell (C/O/R/E) ─────────────────────────────────────────────────────
export function GradeCell({ letter, value, name, color, compact }: { letter: string; value: React.ReactNode; name: string; color: string; compact?: boolean }) {
  return (
    <div style={{ flex: 1, background: VT.bluePanel, border: `1px solid ${VT.lineFaint}`, padding: compact ? '10px 8px' : '14px 12px', textAlign: 'center' }}>
      <div style={{ fontFamily: VT.anton, fontSize: 15, color: VT.lineDim }}>{letter}</div>
      <div style={{ fontFamily: VT.anton, fontSize: compact ? 24 : 32, marginTop: 4, color }}>{value}</div>
      <div style={{ fontSize: 8.5, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 3 }}>{name}</div>
    </div>
  );
}

// ── Redact (confidential-dossier bar) ────────────────────────────────────────
export function Redact({ children }: { children: string }) {
  return (
    <span style={{
      display: 'inline-block', background: 'rgba(10,16,26,0.92)', color: 'transparent',
      borderRadius: 1, userSelect: 'none', boxShadow: '0 0 0 1px rgba(255,255,255,0.08)', verticalAlign: 'baseline',
    }}>
      {children}
    </span>
  );
}

// ── Stamp (confidential / declassified) ──────────────────────────────────────
export function Stamp({ children, kind }: { children: React.ReactNode; kind: 'red' | 'green' }) {
  const isRed = kind === 'red';
  return (
    <div style={{
      fontFamily: VT.oswald, fontWeight: 600, fontSize: 11, letterSpacing: '0.24em', textTransform: 'uppercase',
      color: isRed ? VT.hard : VT.rapport,
      border: `2px solid ${isRed ? VT.hard : VT.rapport}`,
      padding: '5px 14px',
      transform: `rotate(${isRed ? -2 : 2}deg)`,
      display: 'inline-block',
      boxShadow: isRed ? '0 0 12px rgba(228,87,74,0.25), inset 0 0 12px rgba(228,87,74,0.12)' : undefined,
    }}>
      {children}
    </div>
  );
}
