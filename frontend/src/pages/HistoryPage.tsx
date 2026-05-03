import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { History, ArrowLeft, Dumbbell, Trophy, Filter } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { sessionService } from '@/services/sessionService';
import { SessionSummary, SessionType } from '@/types';
import SessionCard from '@/components/SessionCard';
import SessionDetailModal from '@/components/SessionDetailModal';
import UserMenu from '@/components/UserMenu';
import { AT } from '@/styles/tokens';

const HistoryPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { accessToken } = useAuth();

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<SessionType | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const limit = 20;

  const fetchSessions = useCallback(async (fetchOffset: number, append: boolean = false) => {
    if (!accessToken) return;

    try {
      setLoading(true);
      setError(null);

      const response = await sessionService.listSessions(accessToken, {
        limit,
        offset: fetchOffset,
        sessionType: filter || undefined,
      });

      if (append) {
        setSessions(prev => [...prev, ...response.sessions]);
      } else {
        setSessions(response.sessions);
      }

      setOffset(fetchOffset);
      setHasMore(response.hasMore);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, [accessToken, filter]);

  useEffect(() => {
    fetchSessions(0);
  }, [filter, accessToken]);

  const handleLoadMore = () => {
    fetchSessions(offset + limit, true);
  };

  const handleSessionClick = (sessionId: string) => {
    navigate(`/history/${sessionId}`);
  };

  const handleCloseModal = () => {
    navigate('/history');
  };

  const handleFetchSession = useCallback(async (sessionId: string) => {
    if (!accessToken) throw new Error('Not authenticated');
    return sessionService.getSessionDetail(accessToken, sessionId);
  }, [accessToken]);

  const handleFilterChange = (newFilter: SessionType | null) => {
    setFilter(newFilter);
    setOffset(0);
  };

  const filterBtn = (label: string, value: SessionType | null, icon?: React.ReactNode) => (
    <button
      onClick={() => handleFilterChange(value)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '7px 14px', borderRadius: 8,
        background: filter === value ? AT.surface2 : 'transparent',
        border: `1px solid ${filter === value ? AT.hair : AT.hairSoft}`,
        color: filter === value ? AT.ink : AT.inkSoft,
        fontFamily: AT.mono, fontSize: 11,
        letterSpacing: '0.1em', textTransform: 'uppercase',
        cursor: 'pointer',
        transition: 'background 0.15s, border-color 0.15s',
      }}
    >
      {icon}{label}
    </button>
  );

  return (
    <div style={{ minHeight: '100vh', background: AT.bg, color: AT.ink, fontFamily: AT.sans }}>
      {/* Nav */}
      <div style={{
        height: 60, padding: '0 28px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: `1px solid ${AT.hair}`,
        background: AT.surface,
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button
            onClick={() => navigate('/')}
            style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'transparent', border: `1px solid ${AT.hair}`,
              color: AT.ink, cursor: 'pointer',
              display: 'grid', placeItems: 'center',
            }}
          >
            <ArrowLeft size={16} />
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: AT.butter, marginRight: 2,
            }} />
            <span style={{ fontFamily: AT.display, fontSize: 18, fontWeight: 600, letterSpacing: '-0.01em' }}>
              Session History
            </span>
          </div>
        </div>
        <UserMenu />
      </div>

      {/* Body */}
      <div style={{ padding: '28px 40px 48px' }}>
        {/* Filter bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
          <Filter size={14} style={{ color: AT.inkMuted }} />
          <span style={{ fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted, letterSpacing: '0.14em', textTransform: 'uppercase' }}>
            Filter:
          </span>
          {filterBtn('All', null)}
          {filterBtn('Practice', 'training', <Dumbbell size={12} />)}
          {filterBtn('Evaluation', 'evaluation', <Trophy size={12} />)}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: '14px 18px', borderRadius: 10, marginBottom: 20,
            background: AT.terra + '18', border: `1px solid ${AT.terra}40`,
            color: AT.terra, fontSize: 14,
          }}>
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && sessions.length === 0 && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '80px 0',
            fontFamily: AT.mono, fontSize: 11,
            color: AT.inkMuted, letterSpacing: '0.12em', textTransform: 'uppercase',
          }}>
            Loading sessions...
          </div>
        )}

        {/* Empty */}
        {!loading && sessions.length === 0 && !error && (
          <div style={{
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            padding: '80px 0', opacity: 0.5, textAlign: 'center',
          }}>
            <History size={48} style={{ color: AT.inkMuted, marginBottom: 16 }} />
            <p style={{ fontFamily: AT.display, fontSize: 22, fontWeight: 600, color: AT.ink, marginBottom: 8 }}>
              No sessions yet
            </p>
            <p style={{ color: AT.inkSoft, fontSize: 14 }}>
              Start your first practice session to see your history here
            </p>
          </div>
        )}

        {/* Grid */}
        {sessions.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: 16,
          }}>
            {sessions.map(session => (
              <SessionCard
                key={session.sessionId}
                session={session}
                onClick={handleSessionClick}
              />
            ))}
          </div>
        )}

        {/* Load more */}
        {hasMore && !loading && (
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: 32 }}>
            <button
              onClick={handleLoadMore}
              style={{
                padding: '10px 28px', borderRadius: 8,
                background: AT.surface2, color: AT.ink,
                border: `1px solid ${AT.hair}`,
                fontFamily: AT.mono, fontSize: 11,
                letterSpacing: '0.12em', textTransform: 'uppercase',
                cursor: 'pointer',
              }}
            >
              Load More
            </button>
          </div>
        )}

        {loading && sessions.length > 0 && (
          <div style={{
            display: 'flex', justifyContent: 'center', marginTop: 32,
            fontFamily: AT.mono, fontSize: 11,
            color: AT.inkMuted, letterSpacing: '0.1em', textTransform: 'uppercase',
          }}>
            Loading more...
          </div>
        )}
      </div>

      {sessionId && (
        <SessionDetailModal
          sessionId={sessionId}
          onClose={handleCloseModal}
          onFetchSession={handleFetchSession}
        />
      )}
    </div>
  );
};

export default HistoryPage;
