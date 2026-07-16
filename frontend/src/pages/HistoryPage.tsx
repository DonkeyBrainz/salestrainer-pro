import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { sessionService } from '@/services/sessionService';
import { SessionSummary, SessionType, SessionDetail } from '@/types';
import SessionDetailModal from '@/components/SessionDetailModal';
import UserMenu from '@/components/UserMenu';
import { VT, scoreColor } from '@/styles/voiceprint';
import {
  Panel, PanelTitle, StickyNote, NavTag, Cta, FrameLabel, ModeTag, Scribble,
  BlueprintTable, bpThStyle, bpTdStyle, KpiCard,
} from '@/components/voiceprint/primitives';

const DAY = 86400000;
const LIMIT = 50;

const STAGE_ORDER = ['CONNECT', 'OBSERVE', 'RECOMMEND', 'EXECUTE'] as const;
const STAGE_LABEL: Record<string, string> = {
  CONNECT: 'Connect', OBSERVE: 'Observe', RECOMMEND: 'Recommend', EXECUTE: 'Execute',
};
const STAGE_TIP: Record<string, string> = {
  CONNECT: 'Warm up faster — open with genuine curiosity before pitching.',
  OBSERVE: 'Slow down discovery — ask one more question before recommending.',
  RECOMMEND: 'Tie the recommendation directly to what they told you, not a script.',
  EXECUTE: 'Drill closing next steps with a high-regard customer.',
};

function personaKey(s: SessionSummary): string {
  return s.personaName ?? s.selectedPersona ?? s.sessionId;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatLen(seconds: number | null): string {
  if (!seconds) return '—';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function avgScore(list: SessionSummary[]): number | null {
  const scored = list.filter((s): s is SessionSummary & { score: number } => s.score != null);
  if (!scored.length) return null;
  return scored.reduce((sum, s) => sum + s.score, 0) / scored.length;
}

function pickQuote(detail: SessionDetail | null): string | null {
  if (!detail) return null;
  const modelMsgs = detail.transcript.messages.filter((m) => m.role === 'model' && m.text.trim());
  if (!modelMsgs.length) return null;
  return modelMsgs.reduce((longest, m) => (m.text.length > longest.text.length ? m : longest)).text;
}

interface PatternNote {
  stage: string;
  count: number;
  total: number;
}

const HistoryPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { accessToken } = useAuth();

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<SessionType | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<SessionDetail | null>(null);
  const [overlayDelta, setOverlayDelta] = useState<string | null>(null);
  const [pattern, setPattern] = useState<PatternNote | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    sessionService.listSessions(accessToken, { limit: LIMIT, sessionType: filter || undefined })
      .then((response) => {
        if (cancelled) return;
        setSessions(response.sessions);
        setSelectedId(response.sessions[0]?.sessionId ?? null);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load sessions');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [accessToken, filter]);

  const personaBest = useMemo(() => {
    const map = new Map<string, number>();
    sessions.forEach((s) => {
      if (s.score == null) return;
      const key = personaKey(s);
      const cur = map.get(key);
      if (cur == null || s.score > cur) map.set(key, s.score);
    });
    return map;
  }, [sessions]);

  const deltaFor = useCallback((s: SessionSummary): { label: string; up: boolean } | null => {
    if (s.score == null) return null;
    const best = personaBest.get(personaKey(s));
    if (best == null) return null;
    if (s.score >= best) return { label: '★ best', up: true };
    return { label: `${s.score - best}`, up: false };
  }, [personaBest]);

  const handleFetchSession = useCallback(async (id: string) => {
    if (!accessToken) throw new Error('Not authenticated');
    return sessionService.getSessionDetail(accessToken, id);
  }, [accessToken]);

  // Side detail sheet — follows selectedId
  useEffect(() => {
    if (!accessToken || !selectedId) { setSelectedDetail(null); return; }
    let cancelled = false;
    handleFetchSession(selectedId)
      .then((detail) => { if (!cancelled) setSelectedDetail(detail); })
      .catch(() => { if (!cancelled) setSelectedDetail(null); });
    return () => { cancelled = true; };
  }, [accessToken, selectedId, handleFetchSession]);

  // "Pattern spotted" heuristic — weakest CORE stage across last 5 graded sessions
  useEffect(() => {
    if (!accessToken || sessions.length === 0) { setPattern(null); return; }
    const graded = sessions.filter((s) => s.hasEvaluation).slice(0, 5);
    if (graded.length < 3) { setPattern(null); return; }
    let cancelled = false;
    Promise.all(graded.map((s) => handleFetchSession(s.sessionId).catch(() => null)))
      .then((details) => {
        if (cancelled) return;
        const counts: Record<string, number> = {};
        let total = 0;
        details.forEach((d) => {
          const stageScores = d?.evaluation?.scorecard.stage_scores;
          if (!stageScores) return;
          total += 1;
          let weakestStage: string | null = null;
          let weakestScore = Infinity;
          STAGE_ORDER.forEach((stage) => {
            const stat = stageScores[stage];
            if (stat && stat.score < weakestScore) { weakestScore = stat.score; weakestStage = stage; }
          });
          if (weakestStage) counts[weakestStage] = (counts[weakestStage] ?? 0) + 1;
        });
        if (total < 3) { setPattern(null); return; }
        const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
        if (!top || top[1] < 2) { setPattern(null); return; }
        setPattern({ stage: top[0], count: top[1], total });
      });
    return () => { cancelled = true; };
  }, [accessToken, sessions, handleFetchSession]);

  const handleRowClick = (s: SessionSummary) => {
    setSelectedId(s.sessionId);
    const delta = deltaFor(s);
    setOverlayDelta(delta ? (delta.up ? '★ personal best' : `Δ best ${delta.label}`) : null);
    navigate(`/history/${s.sessionId}`);
  };

  const handleCloseModal = () => navigate('/history');

  const now = Date.now();
  const daysAgo = (iso: string) => (now - new Date(iso).getTime()) / DAY;
  const window30 = sessions.filter((s) => daysAgo(s.startedAt) <= 30);
  const windowPrev30 = sessions.filter((s) => daysAgo(s.startedAt) > 30 && daysAgo(s.startedAt) <= 60);

  const practiceCount = window30.filter((s) => s.sessionType === 'training').length;
  const assessCount = window30.filter((s) => s.sessionType === 'evaluation').length;
  const bestSession = window30.reduce<SessionSummary | null>((best, s) => {
    if (s.score == null) return best;
    if (!best || (best.score ?? -1) < s.score) return s;
    return best;
  }, null);
  const avg30 = avgScore(window30);
  const avgPrev = avgScore(windowPrev30);
  const trend = avg30 != null && avgPrev != null ? Math.round(avg30 - avgPrev) : null;

  const selectedSummary = sessions.find((s) => s.sessionId === selectedId) ?? null;
  const quote = pickQuote(selectedDetail);

  const filterBtn = (label: string, value: SessionType | null) => (
    <Cta variant={filter === value ? 'active' : 'ghost'} onClick={() => setFilter(value)} style={{ padding: '8px 16px', fontSize: 10.5 }}>
      {label}
    </Cta>
  );

  return (
    <div style={{ width: '100%', minHeight: '100vh', color: VT.text }}>
      <style>{`
        .arch-row { cursor: pointer; }
        .arch-row td { transition: background .12s ease; }
        .arch-row:hover td { background: rgba(255,255,255,0.04); }
        .arch-row.sel td { background: rgba(240,162,78,0.08); }
      `}</style>

      <div style={{ padding: '32px 40px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <NavTag lobby onClick={() => navigate('/')}>◂ Lobby</NavTag>
          <div style={{ fontFamily: VT.anton, fontSize: 'clamp(22px,2.6vw,36px)', color: VT.text }}>
            SESSION ARCHIVE
          </div>
          <div style={{ fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: VT.textMuted, marginTop: 6 }}>
            transcripts + scorecards · last 30 days
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
          <Scribble>« rm 03 — the filing room</Scribble>
          <UserMenu />
        </div>
      </div>

      <div style={{ padding: '4px 40px 48px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          {filterBtn('All', null)}
          {filterBtn('Practice', 'training')}
          {filterBtn('Assessment', 'evaluation')}
        </div>

        {error && (
          <div style={{ padding: '14px 18px', marginBottom: 20, border: `1px solid ${VT.hard}66`, background: 'rgba(228,87,74,0.1)', color: VT.hard, fontSize: 13 }}>
            {error}
          </div>
        )}

        {loading && sessions.length === 0 && (
          <div style={{ padding: '80px 0', textAlign: 'center', fontFamily: VT.mono, fontSize: 11, color: VT.textMuted, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            Loading sessions…
          </div>
        )}

        {!loading && sessions.length === 0 && !error && (
          <div style={{ padding: '80px 0', textAlign: 'center' }}>
            <div style={{ fontFamily: VT.anton, fontSize: 24, color: VT.text, marginBottom: 8 }}>No sessions yet</div>
            <div style={{ color: VT.textMuted, fontSize: 13 }}>Start your first practice session to see your history here.</div>
          </div>
        )}

        {sessions.length > 0 && (
          <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 480, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <KpiCard
                  label="Sessions · 30d"
                  value={window30.length}
                  sub={`${practiceCount} practice · ${assessCount} assessment${assessCount === 1 ? '' : 's'}`}
                />
                <KpiCard
                  label="Best score"
                  value={bestSession?.score ?? '—'}
                  color={bestSession ? scoreColor(bestSession.score) : undefined}
                  sub={bestSession ? `${bestSession.personaName ?? 'Unknown'} · ${bestSession.sessionType === 'evaluation' ? 'assessment' : 'practice'}` : 'no scored sessions yet'}
                />
                <KpiCard
                  label="Trend"
                  value={trend != null ? `${trend > 0 ? '+' : ''}${trend}` : '—'}
                  color={trend != null ? (trend >= 0 ? VT.rapport : VT.hard) : undefined}
                  sub={trend != null ? 'vs previous 30d' : 'not enough history yet'}
                />
              </div>

              <Panel>
                <PanelTitle dot={VT.amber}>
                  Session log — newest first
                  <span style={{ marginLeft: 'auto', fontFamily: VT.mono, fontSize: 9 }}>SHEET A-03</span>
                </PanelTitle>
                <BlueprintTable>
                  <thead>
                    <tr>
                      <th style={bpThStyle}>Date</th>
                      <th style={bpThStyle}>Customer</th>
                      <th style={bpThStyle}>Mode</th>
                      <th style={bpThStyle}>Length</th>
                      <th style={bpThStyle}>Score</th>
                      <th style={bpThStyle}>Δ Best</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((s) => {
                      const delta = deltaFor(s);
                      return (
                        <tr
                          key={s.sessionId}
                          className={`arch-row${s.sessionId === selectedId ? ' sel' : ''}`}
                          onClick={() => handleRowClick(s)}
                        >
                          <td style={{ ...bpTdStyle, color: VT.textMuted }}>{formatDate(s.startedAt)}</td>
                          <td style={bpTdStyle}>{s.personaName ?? 'Unknown'}</td>
                          <td style={bpTdStyle}><ModeTag mode={s.sessionType === 'evaluation' ? 'assess' : 'practice'} /></td>
                          <td style={{ ...bpTdStyle, color: VT.textMuted }}>{formatLen(s.duration)}</td>
                          <td style={{ ...bpTdStyle, fontFamily: VT.anton, fontSize: 17, color: scoreColor(s.score) }}>{s.score ?? '—'}</td>
                          <td style={{ ...bpTdStyle, color: delta ? (delta.up ? VT.rapport : VT.hard) : VT.textMuted }}>
                            {delta ? delta.label : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </BlueprintTable>
              </Panel>
              <FrameLabel>FIG. 05 — SESSION LOG, {sessions.length} ENTRIES · SCALE N/A</FrameLabel>
            </div>

            <div style={{ width: 320, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
              {selectedSummary && (
                <Panel>
                  <PanelTitle dot={VT.amber}>
                    Scorecard — {formatDate(selectedSummary.startedAt)}
                    <span style={{ marginLeft: 'auto', fontFamily: VT.mono, fontSize: 9 }}>
                      {selectedSummary.sessionType === 'evaluation' ? 'ASSESSMENT' : 'PRACTICE'}
                    </span>
                  </PanelTitle>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                    <span style={{ fontFamily: VT.anton, fontSize: 44, color: scoreColor(selectedSummary.score) }}>
                      {selectedSummary.score ?? '—'}
                    </span>
                    <span style={{ fontSize: 10, color: VT.textMuted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                      {selectedSummary.personaName ?? 'Unknown'} · {formatLen(selectedSummary.duration)}
                    </span>
                  </div>
                  {quote && (
                    <div style={{ fontFamily: VT.oswald, fontSize: 12.5, fontStyle: 'italic', borderLeft: `2px solid ${VT.amber}`, paddingLeft: 12, marginTop: 14, color: VT.text, lineHeight: 1.5 }}>
                      &ldquo;{quote}&rdquo;
                    </div>
                  )}
                  <div style={{ fontSize: 10.5, lineHeight: 1.7, color: VT.textMuted, marginTop: 12 }}>
                    {selectedDetail?.evaluation?.summary ?? (selectedSummary.hasEvaluation ? 'No summary recorded.' : 'Not yet graded.')}
                  </div>
                </Panel>
              )}
              <StickyNote title="Pattern spotted" width="100%" rotate={2}>
                {pattern
                  ? `${STAGE_LABEL[pattern.stage]} is your weakest phase in ${pattern.count} of the last ${pattern.total} graded sessions. ${STAGE_TIP[pattern.stage]}`
                  : 'Not enough graded sessions yet to spot a pattern — keep training.'}
              </StickyNote>
            </div>
          </div>
        )}
      </div>

      {sessionId && (
        <SessionDetailModal
          sessionId={sessionId}
          onClose={handleCloseModal}
          onFetchSession={handleFetchSession}
          deltaLabel={overlayDelta}
        />
      )}
    </div>
  );
};

export default HistoryPage;
