import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { fetchUserStats } from '@/services/statsService';
import type { UserStatsResponse } from '@/types/stats';
import { VT } from '@/styles/voiceprint';
import { FrameLabel, StickyNote } from '@/components/voiceprint/primitives';
import { getEnabledRoles } from '@/components/dashboard/DashboardChrome';
import UserMenu from '@/components/UserMenu';

const ADMIN_EMAILS = ['user@example.com'];

const STAGE_CONFIG: Record<string, { letter: string; name: string }> = {
  CONNECT: { letter: 'C', name: 'Connect' },
  OBSERVE: { letter: 'O', name: 'Observe' },
  RECOMMEND: { letter: 'R', name: 'Recommend' },
  EXECUTE: { letter: 'E', name: 'Execute' },
};

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}

interface RoomProps {
  id: string;
  num: string;
  name: string;
  sub: string;
  x: number;
  y: number;
  w: number;
  h: number;
  restricted?: boolean;
  onClick?: () => void;
  children?: React.ReactNode;
}

function Room({ id, num, name, sub, x, y, w, h, restricted, onClick, children }: RoomProps) {
  return (
    <g
      className="vp-room"
      style={{ cursor: restricted ? 'default' : 'pointer' }}
      onClick={restricted ? undefined : onClick}
    >
      <rect x={x} y={y} width={w} height={h} className="vp-room-fill" fill="transparent" />
      <text x={x + 28} y={y + 38} fontFamily={VT.mono} fontSize={10} letterSpacing="0.14em" fill={VT.amber} opacity={restricted ? 0.4 : 1}>
        {num}
      </text>
      <text x={x + 28} y={y + 73} fontFamily={VT.anton} fontSize={23} letterSpacing="0.03em" fill={VT.line} opacity={restricted ? 0.35 : 1}>
        {name}
      </text>
      <text x={x + 28} y={y + 94} fontFamily={VT.mono} fontSize={10} letterSpacing="0.1em" fill={restricted ? VT.hard : VT.textMuted} opacity={restricted ? 0.75 : 1}>
        {restricted ? 'RESTRICTED · NO ACCESS' : sub}
      </text>
      {!restricted && children}
    </g>
  );
}

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

  const isAdmin = !!user && ADMIN_EMAILS.some((e) => e.toLowerCase() === user.email?.toLowerCase());
  const enabledRoles = getEnabledRoles(user, isAdmin);
  const managerEnabled = enabledRoles.includes('Manager');
  const adminEnabled = enabledRoles.includes('Admin');

  const coreBars = stats?.core_mastery ?? [
    { stage: 'CONNECT', mastery_pct: 0, delta: null },
    { stage: 'OBSERVE', mastery_pct: 0, delta: null },
    { stage: 'RECOMMEND', mastery_pct: 0, delta: null },
    { stage: 'EXECUTE', mastery_pct: 0, delta: null },
  ];

  const bestStage = stats
    ? [...stats.core_mastery].sort((a, b) => (b.delta ?? 0) - (a.delta ?? 0))[0]
    : null;
  const coachNote = bestStage && (bestStage.delta ?? 0) > 0
    ? `Your ${STAGE_CONFIG[bestStage.stage]?.name ?? bestStage.stage} scores climbed ${bestStage.delta!.toFixed(0)} pts this week. Try a high-regard customer to push further.`
    : stats
    ? 'Complete more sessions to unlock personalized coaching notes.'
    : 'Complete your first session to see your C.O.R.E. breakdown here.';

  const firstName = (user?.name ?? 'there').split(' ')[0];
  const avgScore = stats?.avg_score_this_week;

  return (
    <div style={{ width: '100%', minHeight: '100vh', color: VT.text, display: 'flex', flexDirection: 'column' }}>
      <style>{`
        .vp-room:hover .vp-room-fill { fill: rgba(255,255,255,0.07); }
      `}</style>

      <div style={{ padding: '32px 40px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div style={{ fontFamily: VT.anton, fontSize: 'clamp(24px,3vw,40px)', letterSpacing: '0.02em', color: VT.line, textShadow: '0 0 18px rgba(255,255,255,0.18)' }}>
            SALESTRAINER
          </div>
          <div style={{ fontFamily: VT.caveat, fontSize: 20, color: VT.amber, marginLeft: 4, marginTop: -4 }}>
            an AI voice coach for real estate
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
          <div style={{ fontFamily: VT.caveat, fontSize: 22, color: VT.lineDim }}>
            « {greeting()}, {firstName} — pick a room
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, letterSpacing: '0.05em', color: VT.textMuted }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: VT.special, display: 'inline-block' }} />
              Avg score <b style={{ color: VT.text, fontFamily: VT.oswald, fontSize: 14, fontWeight: 600 }}>{avgScore != null ? Math.round(avgScore) : '—'}</b>
            </div>
            <UserMenu />
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 44, minHeight: 0, padding: '0 40px 26px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, minWidth: 0 }}>
          <svg viewBox="0 0 940 640" xmlns="http://www.w3.org/2000/svg" style={{ height: 'min(66vh, 560px)', maxWidth: '100%' }}>
            <rect x={40} y={30} width={840} height={540} stroke={VT.line} strokeWidth={2.5} fill="none" />

            <path d="M 470 30 L 470 130 M 470 190 L 470 300" stroke="rgba(255,255,255,0.7)" strokeWidth={1.6} fill="none" />
            <path d="M 40 300 L 200 300 M 260 300 L 560 300 M 620 300 L 880 300" stroke="rgba(255,255,255,0.7)" strokeWidth={1.6} fill="none" />
            <path d="M 330 300 L 330 430 M 330 490 L 330 570" stroke="rgba(255,255,255,0.7)" strokeWidth={1.6} fill="none" />
            <path d="M 610 300 L 610 380 M 610 440 L 610 570" stroke="rgba(255,255,255,0.7)" strokeWidth={1.6} fill="none" />

            <path d="M 470 130 A 60 60 0 0 1 530 190" stroke={VT.lineDim} strokeWidth={1} strokeDasharray="3 3" fill="none" transform="rotate(90 470 160)" />
            <path d="M 200 300 A 60 60 0 0 1 260 360" stroke={VT.lineDim} strokeWidth={1} strokeDasharray="3 3" fill="none" />

            <Room id="roomLive" num="RM 01" name="LIVE PRACTICE" sub="COACHED · CUES + MOOD READ" x={42} y={32} w={426} h={266} onClick={() => navigate('/training')}>
              <rect x={290} y={180} width={120} height={56} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <circle cx={330} cy={164} r={11} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <circle cx={372} cy={252} r={11} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <path d="M 70 200 q 24 -18 48 0 q -24 18 -48 0" stroke={VT.lineDim} strokeWidth={1} fill="none" />
            </Room>

            <Room id="roomAssess" num="RM 02" name="PERFORMANCE ASSESSMENT" sub="NO HINTS · GRADED END-TO-END" x={472} y={32} w={406} h={266} onClick={() => navigate('/evaluation')}>
              <rect x={740} y={170} width={100} height={46} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <rect x={762} y={230} width={56} height={36} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <path d="M 766 240 h 48 M 766 250 h 48 M 766 260 h 30" stroke={VT.lineDim} strokeWidth={1} fill="none" />
            </Room>

            <Room id="roomHistory" num="RM 03" name="SESSION ARCHIVE" sub="TRANSCRIPTS + SCORECARDS" x={42} y={302} w={286} h={266} onClick={() => navigate('/history')}>
              <rect x={70} y={470} width={180} height={18} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <rect x={70} y={496} width={180} height={18} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <rect x={70} y={522} width={180} height={18} stroke={VT.lineDim} strokeWidth={1} fill="none" />
            </Room>

            <Room
              id="roomManager"
              num="RM 04"
              name="MANAGER OFFICE"
              sub={`TEAM ROSTER${user?.storeId ? ` · ${user.storeId}` : ''}`}
              x={332} y={302} w={276} h={266}
              restricted={!managerEnabled}
              onClick={() => navigate('/team/manager')}
            >
              <rect x={360} y={480} width={110} height={46} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <rect x={500} y={430} width={80} height={56} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <path d="M 508 444 h 30 M 508 456 h 46 M 508 468 h 38" stroke={VT.lineDim} strokeWidth={1} fill="none" />
            </Room>

            <Room
              id="roomAdmin"
              num="RM 05"
              name="ADMIN WING"
              sub="REGIONAL SURVEY"
              x={612} y={302} w={266} h={266}
              restricted={!adminEnabled}
              onClick={() => navigate('/team/admin')}
            >
              <rect x={660} y={450} width={160} height={80} stroke={VT.lineDim} strokeWidth={1} fill="none" />
              <path d="M 676 470 l 30 20 l 26 -12 l 34 24 M 700 520 l 22 -16" stroke={VT.lineDim} strokeWidth={1} fill="none" />
            </Room>

            <line x1={40} y1={600} x2={880} y2={600} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
            <line x1={40} y1={595} x2={40} y2={605} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
            <line x1={880} y1={595} x2={880} y2={605} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
            <text x={460} y={592} textAnchor="middle" fontFamily={VT.mono} fontSize={9.5} letterSpacing="0.06em" fill="rgba(255,255,255,0.6)">64&apos;-0&quot;</text>
            <line x1={912} y1={30} x2={912} y2={570} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
            <line x1={907} y1={30} x2={917} y2={30} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
            <line x1={907} y1={570} x2={917} y2={570} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
            <text x={928} y={304} textAnchor="middle" fontFamily={VT.mono} fontSize={9.5} letterSpacing="0.06em" fill="rgba(255,255,255,0.6)" transform="rotate(90 928 304)">41&apos;-0&quot;</text>
          </svg>
          <FrameLabel>FIG. 01 — <b style={{ color: VT.text }}>TRAINING FLOOR</b>, PLAN VIEW · SCALE 1:100 · CLICK A ROOM TO ENTER</FrameLabel>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, width: 250, flexShrink: 0 }}>
          <div>
            <FrameLabel><div style={{ textAlign: 'left', marginBottom: 12 }}>C.O.R.E. mastery · 30d</div></FrameLabel>
            <div style={{ display: 'flex', gap: 16, justifyContent: 'flex-start' }}>
              {coreBars.map((stage) => {
                const cfg = STAGE_CONFIG[stage.stage];
                if (!cfg) return null;
                return (
                  <div key={stage.stage} style={{ textAlign: 'center' }}>
                    <div style={{ fontFamily: VT.anton, fontSize: 14, color: VT.lineDim }}>{cfg.letter}</div>
                    <div style={{ fontFamily: VT.oswald, fontSize: 19, fontWeight: 600, color: VT.line }}>{Math.round(stage.mastery_pct)}</div>
                    <div style={{ fontSize: 8.5, letterSpacing: '0.14em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 2 }}>{cfg.name}</div>
                  </div>
                );
              })}
            </div>
          </div>
          <StickyNote title="Coach's note">{coachNote}</StickyNote>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
