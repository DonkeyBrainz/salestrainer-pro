import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { fetchUserStats } from '@/services/statsService';
import type { UserStatsResponse, COREStageStats } from '@/types/stats';
import { AT } from '@/styles/tokens';

// ── Design tokens ─────────────────────────────────────────────────────────────

const STAGE_CONFIG: Record<string, { letter: string; name: string; color: string }> = {
  CONNECT:   { letter: 'C', name: 'Connect',   color: AT.sage },
  OBSERVE:   { letter: 'O', name: 'Observe',   color: AT.terra },
  RECOMMEND: { letter: 'R', name: 'Recommend', color: AT.butter },
  EXECUTE:   { letter: 'E', name: 'Execute',   color: AT.inkMuted },
};

const GRADE_COLOR: Record<string, string> = {
  A: AT.sage,
  B: '#7ab87a',
  C: AT.butter,
  D: AT.terra,
  F: AT.terra,
};

function gradeColor(grade: string | null): string {
  return grade ? (GRADE_COLOR[grade] ?? AT.inkMuted) : AT.inkMuted;
}

function formatDelta(delta: number | null): { text: string; positive: boolean } {
  if (delta === null) return { text: '—', positive: true };
  return { text: `${delta > 0 ? '+' : ''}${delta.toFixed(0)}`, positive: delta >= 0 };
}

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  return `${days}d ago`;
}

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

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

function StreakDots({ sessionsThisWeek, weeklyGoal }: { sessionsThisWeek: number; weeklyGoal: number }) {
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', width: 98 }}>
      {Array.from({ length: weeklyGoal }).map((_, i) => (
        <div
          key={i}
          style={{
            width: 8, height: 8, borderRadius: '50%',
            background: i < sessionsThisWeek ? AT.terra : AT.hair,
          }}
        />
      ))}
    </div>
  );
}

function WeekBars({ sessionsThisWeek, weeklyGoal }: { sessionsThisWeek: number; weeklyGoal: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 40 }}>
      {Array.from({ length: weeklyGoal }).map((_, i) => (
        <div
          key={i}
          style={{
            width: 8,
            height: i < sessionsThisWeek ? `${60 + Math.random() * 40}%` : '10%',
            background: i < sessionsThisWeek ? AT.sage : AT.hair,
            borderRadius: 2,
            opacity: i < sessionsThisWeek ? 1 : 0.4,
          }}
        />
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
  num, tag, title, desc, accent, cta, onClick,
}: {
  num: string; tag: string; title: string; desc: string;
  accent: string; cta: string; onClick: () => void;
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
function SkillBar({ stage }: { stage: COREStageStats }) {
  const config = STAGE_CONFIG[stage.stage];
  if (!config) return null;
  const { text: deltaText, positive } = formatDelta(stage.delta);
  const pct = Math.round(stage.mastery_pct);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '36px 1fr 56px 50px', alignItems: 'center', gap: 14 }}>
      <div style={{
        width: 36, height: 36, borderRadius: 8,
        background: config.color + '22', color: config.color,
        fontFamily: AT.display, fontSize: 18, fontWeight: 700,
        display: 'grid', placeItems: 'center',
      }}>
        {config.letter}
      </div>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
          <div style={{ fontFamily: AT.mono, fontSize: 11, letterSpacing: '0.14em', color: AT.ink, textTransform: 'uppercase' }}>{config.name}</div>
          <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.inkMuted }}>{pct}/100</div>
        </div>
        <div style={{ height: 6, borderRadius: 3, background: AT.hair, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: config.color, boxShadow: `0 0 8px ${config.color}80` }} />
        </div>
      </div>
      <div style={{ fontFamily: AT.mono, fontSize: 11, color: positive ? AT.sage : AT.terra, fontWeight: 600 }}>{deltaText}</div>
      <div style={{ fontFamily: AT.mono, fontSize: 9.5, color: AT.inkMuted, letterSpacing: '0.1em', textAlign: 'right' }}>
        {positive ? 'on track' : 'work on'}
      </div>
    </div>
  );
}

// ── Home Page ─────────────────────────────────────────────────────────────────
const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { accessToken, user } = useAuth();
  const [stats, setStats] = useState<UserStatsResponse | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    fetchUserStats(accessToken)
      .then((data) => { if (!cancelled) setStats(data); })
      .catch(() => { /* stats stay null — static fallbacks remain */ });
    return () => { cancelled = true; };
  }, [accessToken]);

  // Derived display values (fall back to design-spec placeholders while loading)
  const currentStreak  = stats?.current_streak  ?? 0;
  const longestStreak  = stats?.longest_streak  ?? 0;
  const sessionsWeek   = stats?.sessions_this_week ?? 0;
  const weeklyGoal     = stats?.weekly_goal     ?? 7;
  const avgScore       = stats?.avg_score_this_week ?? null;
  const sessionsLeft   = Math.max(0, weeklyGoal - sessionsWeek);

  const userName = user?.name ?? 'there';
  const userInitial = userName[0]?.toUpperCase() ?? '?';

  const streakFoot = longestStreak > 0 && currentStreak >= longestStreak
    ? `Your longest streak ever. Keep it going.`
    : longestStreak > 0
    ? `Record: ${longestStreak} days.`
    : 'Start a streak today.';

  const weekFoot = sessionsLeft === 0
    ? `Weekly goal hit!${avgScore != null ? ` Avg score ${avgScore}.` : ''}`
    : `${sessionsLeft} to go.${avgScore != null ? ` Avg score ${avgScore}.` : ''}`;

  const heroDesc = stats
    ? sessionsLeft === 0
      ? `You hit your weekly goal this week. Push further — keep the streak alive.`
      : `You're ${sessionsLeft} session${sessionsLeft !== 1 ? 's' : ''} from your weekly goal. Streak: ${currentStreak} day${currentStreak !== 1 ? 's' : ''}.`
    : `Start a session to begin tracking your progress.`;

  // Most recently practiced persona for hero
  const latestPersona = stats?.recent_activity?.[0]?.persona_name ?? null;
  const heroSub = latestPersona ? ` ${latestPersona} is waiting.` : '';

  // CORE bars — use live data or zero-state placeholders
  const coreBars: COREStageStats[] = stats?.core_mastery ?? [
    { stage: 'CONNECT',   mastery_pct: 0, delta: null },
    { stage: 'OBSERVE',   mastery_pct: 0, delta: null },
    { stage: 'RECOMMEND', mastery_pct: 0, delta: null },
    { stage: 'EXECUTE',   mastery_pct: 0, delta: null },
  ];

  // Coach note — highlight the best-improving stage
  const bestStage = stats
    ? [...stats.core_mastery].sort((a, b) => (b.delta ?? 0) - (a.delta ?? 0))[0]
    : null;
  const coachNote = bestStage && (bestStage.delta ?? 0) > 0
    ? `Your ${STAGE_CONFIG[bestStage.stage]?.name ?? bestStage.stage} scores climbed ${bestStage.delta!.toFixed(0)} pts. Keep pushing.`
    : stats
    ? 'Complete more sessions to unlock personalized coaching notes.'
    : 'Complete your first session to see your C.O.R.E. breakdown.';

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
          {currentStreak > 0 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 10px', background: AT.surface,
              border: `1px solid ${AT.hair}`, borderRadius: 8,
            }}>
              <div style={{ fontFamily: AT.mono, fontSize: 10, letterSpacing: '0.14em', color: AT.terra, textTransform: 'uppercase' }}>Streak</div>
              <div style={{ width: 1, height: 12, background: AT.hair }} />
              <div style={{ fontFamily: AT.mono, fontSize: 11, color: AT.ink }}>{currentStreak} day{currentStreak !== 1 ? 's' : ''}</div>
            </div>
          )}
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
            }}>{userInitial}</div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{userName.split(' ')[0]}</div>
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
            <div style={{
              position: 'absolute', inset: 0,
              backgroundImage: `linear-gradient(${AT.hair} 1px, transparent 1px), linear-gradient(90deg, ${AT.hair} 1px, transparent 1px)`,
              backgroundSize: '32px 32px',
              opacity: 0.4,
              maskImage: 'radial-gradient(ellipse at top right, black 0%, transparent 70%)',
              WebkitMaskImage: 'radial-gradient(ellipse at top right, black 0%, transparent 70%)',
            }} />

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
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: AT.terra, boxShadow: `0 0 10px ${AT.terra}` }} />
                <div style={{ fontFamily: AT.mono, fontSize: 11, letterSpacing: '0.16em', color: AT.terra, textTransform: 'uppercase', fontWeight: 600 }}>
                  {greeting()}, {userName.split(' ')[0]}
                </div>
              </div>
              <div style={{ fontFamily: AT.display, fontSize: 52, lineHeight: 0.95, letterSpacing: '-0.025em', fontWeight: 600, color: AT.ink }}>
                Ready to <span style={{ color: AT.terra, fontStyle: 'italic' }}>close one</span>?
              </div>
              <div style={{ marginTop: 16, fontSize: 14, color: AT.inkSoft, maxWidth: 460, lineHeight: 1.5 }}>
                {heroDesc}{heroSub}
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
              value={String(currentStreak)}
              unit="days"
              accent={AT.terra}
              right={<StreakDots sessionsThisWeek={sessionsWeek} weeklyGoal={weeklyGoal} />}
              foot={streakFoot}
            />
            <StatCard
              label="This week"
              value={`${sessionsWeek}/${weeklyGoal}`}
              unit="sessions"
              accent={AT.sage}
              right={<WeekBars sessionsThisWeek={sessionsWeek} weeklyGoal={weeklyGoal} />}
              foot={weekFoot}
            />
          </div>
        </div>

        {/* Mode tiles */}
        <div style={{ marginBottom: 28 }}>
          <SectionLabel>Modes</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginTop: 12 }}>
            <ModeTile
              num="01" tag="Coached" title="Live Practice"
              desc="A coached, real-time conversation with on-screen cues, mood read, and CORE prompts."
              accent={AT.sage} cta="Start coached session" onClick={() => navigate('/training')}
            />
            <ModeTile
              num="02" tag="Test yourself" title="Performance Assessment"
              desc="No hints, no coaching. Full conversation graded end-to-end."
              accent={AT.terra} cta="Take assessment" onClick={() => navigate('/evaluation')}
            />
            <ModeTile
              num="03" tag="Look back" title="Session History"
              desc="Replay transcripts, scorecards, and coach notes from past sessions."
              accent={AT.butter} cta="Browse sessions" onClick={() => navigate('/history')}
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
              {coreBars.map((stage) => (
                <SkillBar key={stage.stage} stage={stage} />
              ))}
            </div>
            <div style={{
              marginTop: 18, padding: '12px 14px', borderRadius: 10,
              background: AT.sage + '14',
              border: `1px solid ${AT.sageDim}`,
              fontSize: 13, color: AT.inkSoft, lineHeight: 1.5,
            }}>
              <span style={{ color: AT.sage, marginRight: 6 }}>✦</span>
              <b style={{ color: AT.ink }}>Coach's note:</b> {coachNote}
            </div>
          </div>

          {/* Recent activity */}
          <div style={{ background: AT.surface, border: `1px solid ${AT.hair}`, borderRadius: 14, padding: 22 }}>
            <div style={{ marginBottom: 8 }}>
              <SectionLabel>Recent activity</SectionLabel>
            </div>

            {stats && stats.recent_activity.length === 0 ? (
              <div style={{ paddingTop: 24, textAlign: 'center', color: AT.inkMuted, fontSize: 13 }}>
                No sessions yet. Start one to see your activity here.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {(stats?.recent_activity ?? []).map((session, i) => {
                  const gc = gradeColor(session.grade);
                  return (
                    <div
                      key={session.session_id}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr auto auto',
                        gap: 16,
                        alignItems: 'center',
                        padding: '12px 2px',
                        borderBottom: i < (stats?.recent_activity.length ?? 0) - 1 ? `1px solid ${AT.hair}` : 'none',
                      }}
                    >
                      <div>
                        <div style={{ fontFamily: AT.display, fontSize: 16, fontWeight: 500, color: AT.ink }}>
                          {session.persona_name ?? 'Session'}
                        </div>
                        <div style={{ fontFamily: AT.mono, fontSize: 10.5, color: AT.inkMuted, marginTop: 2, letterSpacing: '0.06em' }}>
                          {formatRelativeTime(session.started_at)}
                        </div>
                      </div>
                      <div style={{
                        background: gc + '22',
                        color: gc,
                        fontFamily: AT.mono, fontSize: 12, fontWeight: 600,
                        padding: '4px 10px', borderRadius: 999,
                      }}>
                        {session.score ?? '—'}
                      </div>
                      <div
                        style={{ color: AT.inkMuted, fontSize: 16, cursor: 'pointer' }}
                        onClick={() => navigate('/history')}
                      >›</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
