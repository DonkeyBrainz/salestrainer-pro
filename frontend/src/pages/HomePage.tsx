import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AT } from '@/styles/tokens';

// ── Logo ──────────────────────────────────────────────────────────────────────
function ArenaLogo() {
  return (
    <div style={{ position: 'relative', width: 30, height: 30, flexShrink: 0 }}>
      <div style={{ position: 'absolute', inset: 0, background: AT.terra, transform: 'rotate(45deg)', borderRadius: 4 }} />
      <div style={{ position: 'absolute', inset: 6, background: AT.bg, transform: 'rotate(45deg)', borderRadius: 2 }} />
      <div style={{ position: 'absolute', inset: 11, background: AT.sage, transform: 'rotate(45deg)', borderRadius: 1 }} />
    </div>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({
  label,
  value,
  unit,
  accent,
  right,
  foot,
}: {
  label: string;
  value: string;
  unit: string;
  accent: string;
  right: React.ReactNode;
  foot: string;
}) {
  return (
    <div style={{
      background: AT.surface,
      border: `1px solid ${AT.hair}`,
      borderRadius: 14,
      padding: '16px 18px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: AT.mono, fontSize: 10, letterSpacing: '0.16em', color: AT.inkMuted, textTransform: 'uppercase' }}>{label}</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 6 }}>
            <div style={{ fontFamily: AT.display, fontSize: 36, color: accent, lineHeight: 1, fontWeight: 700, letterSpacing: '-0.02em' }}>{value}</div>
            <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkSoft }}>{unit}</div>
          </div>
        </div>
        {right}
      </div>
      <div style={{ fontSize: 12, color: AT.inkMuted, marginTop: 10 }}>{foot}</div>
    </div>
  );
}

function StreakDots() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, width: 98 }}>
      {Array.from({ length: 14 }).map((_, i) => (
        <div key={i} style={{ aspectRatio: '1', borderRadius: 3, background: AT.terra, opacity: 0.3 + (i / 14) * 0.7 }} />
      ))}
    </div>
  );
}

function MiniBars() {
  const heights = [40, 70, 30, 90, 60, 80, 0];
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 40 }}>
      {heights.map((h, i) => (
        <div key={i} style={{ width: 8, height: `${h || 10}%`, background: h ? AT.sage : AT.hair, borderRadius: 2, opacity: h ? 1 : 0.4 }} />
      ))}
    </div>
  );
}

// ── Section label ─────────────────────────────────────────────────────────────
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontFamily: AT.mono,
      fontSize: 10.5,
      letterSpacing: '0.18em',
      color: AT.inkMuted,
      textTransform: 'uppercase',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    }}>
      <span style={{ display: 'inline-block', width: 14, height: 1, background: AT.terra }} />
      {String(children).toUpperCase()}
    </div>
  );
}

// ── Mode tile ─────────────────────────────────────────────────────────────────
function ModeTile({
  num,
  tag,
  title,
  desc,
  accent,
  cta,
  onClick,
}: {
  num: string;
  tag: string;
  title: string;
  desc: string;
  accent: string;
  cta: string;
  onClick: () => void;
}) {
  const [hovered, setHovered] = React.useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: AT.surface,
        border: `1px solid ${hovered ? accent + '80' : AT.hair}`,
        borderRadius: 14,
        padding: 20,
        minHeight: 200,
        display: 'flex',
        flexDirection: 'column',
        cursor: 'pointer',
        transform: hovered ? 'translateY(-4px)' : 'translateY(0)',
        transition: 'border-color 0.15s, transform 0.15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}>
        <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted, letterSpacing: '0.16em' }}>{num}</div>
        <div style={{ fontFamily: AT.mono, fontSize: 10, letterSpacing: '0.14em', color: accent, fontWeight: 600, textTransform: 'uppercase' }}>{tag}</div>
      </div>
      <div style={{ fontFamily: AT.display, fontSize: 24, fontWeight: 600, letterSpacing: '-0.015em', color: AT.ink }}>{title}</div>
      <div style={{ marginTop: 8, fontSize: 13, color: AT.inkSoft, lineHeight: 1.5, flex: 1 }}>{desc}</div>
      <div style={{ marginTop: 16, display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: accent, fontWeight: 500 }}>
        {cta} <span>→</span>
      </div>
    </div>
  );
}

// ── Skill bar ─────────────────────────────────────────────────────────────────
function SkillBar({
  letter,
  name,
  pct,
  delta,
  color,
  negative,
}: {
  letter: string;
  name: string;
  pct: number;
  delta: string;
  color: string;
  negative?: boolean;
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '36px 1fr 56px 50px', alignItems: 'center', gap: 14 }}>
      <div style={{
        width: 36, height: 36, borderRadius: 8,
        background: color + '22', color,
        fontFamily: AT.display, fontSize: 18, fontWeight: 700,
        display: 'grid', placeItems: 'center',
      }}>
        {letter}
      </div>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
          <div style={{ fontFamily: AT.mono, fontSize: 11, letterSpacing: '0.14em', color: AT.ink, textTransform: 'uppercase' }}>{name}</div>
          <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted }}>{pct}/100</div>
        </div>
        <div style={{ height: 6, borderRadius: 3, background: AT.hair, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: color, boxShadow: `0 0 8px ${color}80` }} />
        </div>
      </div>
      <div style={{ fontFamily: AT.mono, fontSize: 11, color: negative ? AT.terra : AT.sage, fontWeight: 600 }}>{delta}</div>
      <div style={{ fontFamily: AT.mono, fontSize: 9.5, color: AT.inkMuted, letterSpacing: '0.1em', textAlign: 'right' }}>
        {negative ? 'work on' : 'on track'}
      </div>
    </div>
  );
}

// ── Home Page ─────────────────────────────────────────────────────────────────
const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ width: '100%', minHeight: '100vh', background: AT.bg, color: AT.ink, fontFamily: AT.sans }}>
      {/* Nav */}
      <div style={{
        height: 60, padding: '0 28px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: `1px solid ${AT.hair}`,
        position: 'sticky', top: 0, background: AT.bg, zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <ArenaLogo />
          <div style={{ fontFamily: AT.display, fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>
            SalesTrainer<span style={{ color: AT.terra, fontStyle: 'italic', fontWeight: 500 }}> Pro</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 10px', background: AT.surface,
            border: `1px solid ${AT.hair}`, borderRadius: 8,
          }}>
            <div style={{ fontFamily: AT.mono, fontSize: 10, letterSpacing: '0.14em', color: AT.terra, textTransform: 'uppercase' }}>Streak</div>
            <div style={{ width: 1, height: 12, background: AT.hair }} />
            <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.ink }}>14 days</div>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '4px 12px 4px 4px',
            borderRadius: 999, background: AT.surface, border: `1px solid ${AT.hair}`,
          }}>
            <div style={{
              width: 24, height: 24, borderRadius: '50%',
              background: AT.terra, color: AT.bg,
              display: 'grid', placeItems: 'center',
              fontSize: 11, fontWeight: 700,
            }}>M</div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Mowgli</div>
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '32px 40px 48px' }}>

        {/* Hero strip */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16, marginBottom: 24 }}>
          {/* Mission card */}
          <div style={{
            background: `linear-gradient(135deg, ${AT.surface} 0%, ${AT.surface2} 100%)`,
            border: `1px solid ${AT.hair}`,
            borderRadius: 18,
            padding: 28,
            position: 'relative',
            overflow: 'hidden',
          }}>
            {/* Dotted grid bg */}
            <div style={{
              position: 'absolute', inset: 0,
              backgroundImage: `linear-gradient(${AT.hair} 1px, transparent 1px), linear-gradient(90deg, ${AT.hair} 1px, transparent 1px)`,
              backgroundSize: '32px 32px',
              opacity: 0.4,
              maskImage: 'radial-gradient(ellipse at top right, black 0%, transparent 70%)',
              WebkitMaskImage: 'radial-gradient(ellipse at top right, black 0%, transparent 70%)',
            }} />

            {/* Recommended next */}
            <div style={{
              position: 'absolute', top: 22, right: 22,
              padding: '6px 10px',
              background: AT.sage + '18',
              border: `1px solid ${AT.sageDim}`,
              borderRadius: 8,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <div style={{ width: 5, height: 5, borderRadius: '50%', background: AT.sage }} />
              <div style={{ fontFamily: AT.mono, fontSize: 10, color: AT.sage, letterSpacing: '0.14em', textTransform: 'uppercase' }}>Recommended next</div>
            </div>

            <div style={{ position: 'relative' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                <div className="pulse-dot" style={{ width: 6, height: 6, borderRadius: '50%', background: AT.terra, boxShadow: `0 0 10px ${AT.terra}` }} />
                <div style={{ fontFamily: AT.mono, fontSize: 11, letterSpacing: '0.16em', color: AT.terra, textTransform: 'uppercase', fontWeight: 600 }}>
                  Good morning, Mowgli
                </div>
              </div>
              <div style={{ fontFamily: AT.display, fontSize: 52, lineHeight: 0.95, letterSpacing: '-0.025em', fontWeight: 600, color: AT.ink }}>
                Ready to <span style={{ color: AT.terra, fontStyle: 'italic' }}>close one</span>?
              </div>
              <div style={{ marginTop: 16, fontSize: 14, color: AT.inkSoft, maxWidth: 460, lineHeight: 1.5 }}>
                You're 2 sessions from your weekly goal. Keep the streak alive — Marcus is waiting.
              </div>
              <div style={{ marginTop: 22, display: 'flex', gap: 10 }}>
                <button
                  onClick={() => navigate('/training')}
                  style={{
                    padding: '12px 22px',
                    background: AT.terra, color: AT.bg,
                    border: 'none', borderRadius: 10,
                    fontWeight: 600, fontSize: 13.5, fontFamily: AT.sans,
                    cursor: 'pointer',
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    boxShadow: `0 0 24px ${AT.terra}66`,
                  }}
                >
                  ▶ Start coached session
                </button>
                <button
                  onClick={() => navigate('/evaluation')}
                  style={{
                    padding: '12px 18px',
                    background: 'transparent', color: AT.ink,
                    border: `1px solid ${AT.hair}`, borderRadius: 10,
                    fontWeight: 500, fontSize: 13.5, fontFamily: AT.sans,
                    cursor: 'pointer',
                  }}
                >
                  Take assessment
                </button>
              </div>
            </div>
          </div>

          {/* Stat cards */}
          <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr', gap: 16 }}>
            <StatCard
              label="Streak"
              value="14"
              unit="days"
              accent={AT.terra}
              right={<StreakDots />}
              foot="Your longest yet. Two more days to your record."
            />
            <StatCard
              label="This week"
              value="5/7"
              unit="sessions"
              accent={AT.sage}
              right={<MiniBars />}
              foot="Two to go. Average score 78."
            />
          </div>
        </div>

        {/* Mode tiles */}
        <div style={{ marginBottom: 28 }}>
          <SectionLabel>Modes</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginTop: 12 }}>
            <ModeTile
              num="01"
              tag="Coached"
              title="Live Practice"
              desc="A coached, real-time conversation with on-screen cues, mood read, and CORE prompts."
              accent={AT.sage}
              cta="Start coached session"
              onClick={() => navigate('/training')}
            />
            <ModeTile
              num="02"
              tag="Test yourself"
              title="Performance Assessment"
              desc="No hints, no coaching. Full conversation graded end-to-end."
              accent={AT.terra}
              cta="Take assessment"
              onClick={() => navigate('/evaluation')}
            />
            <ModeTile
              num="03"
              tag="Look back"
              title="Session History"
              desc="Replay transcripts, scorecards, and coach notes from past sessions."
              accent={AT.butter}
              cta="Browse sessions"
              onClick={() => navigate('/history')}
            />
          </div>
        </div>

        {/* CORE mastery + Recent activity */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16 }}>
          {/* CORE mastery */}
          <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: 22 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
              <SectionLabel>C.O.R.E. mastery</SectionLabel>
              <div style={{ fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted, letterSpacing: '0.14em', textTransform: 'uppercase' }}>Last 30 days</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <SkillBar letter="C" name="Connect"     pct={86} delta="+4"  color={AT.sage} />
              <SkillBar letter="O" name="Observe"     pct={72} delta="+12" color={AT.terra} />
              <SkillBar letter="R" name="Recommend"   pct={64} delta="+1"  color={AT.butter} />
              <SkillBar letter="E" name="Execute"     pct={58} delta="-2"  color={AT.inkMuted} negative />
            </div>
            <div style={{
              marginTop: 18, padding: '12px 14px', borderRadius: 10,
              background: AT.sage + '14',
              border: `1px solid ${AT.sageDim}`,
              fontSize: 13, color: AT.inkSoft, lineHeight: 1.5,
            }}>
              <span style={{ color: AT.sage, marginRight: 6 }}>✦</span>
              <b style={{ color: AT.ink }}>Coach's note:</b> Your Observe scores climbed 12 pts this week. Try a high-regard scenario to push Recommend.
            </div>
          </div>

          {/* Recent activity */}
          <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: 22 }}>
            <div style={{ marginBottom: 8 }}>
              <SectionLabel>Recent activity</SectionLabel>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {[
                { name: 'Jennifer', date: 'Tue 2:14p', score: 78, tone: AT.sage },
                { name: 'Alex',     date: 'Mon 4:01p', score: 64, tone: AT.butter },
                { name: 'Marcus',   date: 'Sun 11:30a', score: 91, tone: AT.sage },
                { name: 'Amanda',   date: 'Sat 9:05a', score: 55, tone: AT.terra },
              ].map((r, i) => (
                <div
                  key={i}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr auto auto',
                    gap: 16,
                    alignItems: 'center',
                    padding: '12px 2px',
                    borderBottom: i < 3 ? `1px solid ${AT.hair}` : 'none',
                  }}
                >
                  <div>
                    <div style={{ fontFamily: AT.display, fontSize: 16, fontWeight: 500, color: AT.ink }}>{r.name}</div>
                    <div style={{ fontFamily: AT.mono, fontSize: 10.5, color: AT.inkMuted, marginTop: 2, letterSpacing: '0.06em' }}>{r.date}</div>
                  </div>
                  <div style={{
                    background: r.tone + '22',
                    color: r.tone,
                    fontFamily: AT.mono, fontSize: 12, fontWeight: 600,
                    padding: '4px 10px', borderRadius: 999,
                  }}>
                    {r.score}
                  </div>
                  <div style={{ color: AT.inkMuted, fontSize: 16, cursor: 'pointer' }} onClick={() => navigate('/history')}>›</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
