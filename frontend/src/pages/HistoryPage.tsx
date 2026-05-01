import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { History, ArrowLeft, Dumbbell, Trophy, Filter } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { sessionService } from '@/services/sessionService';
import { SessionSummary, SessionType } from '@/types';
import SessionCard from '@/components/SessionCard';
import SessionDetailModal from '@/components/SessionDetailModal';
import UserMenu from '@/components/UserMenu';
import AmbientBackground from '@/components/AmbientBackground';

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

  return (
    <div className="flex h-screen bg-[#F9F8F6] text-[#2C2825] font-sans overflow-hidden relative">
      <AmbientBackground mode={null} audioLevel={0} sentiment="neutral" />

      <div className="absolute inset-0 flex flex-col z-20 overflow-y-auto custom-scrollbar">
        <header className="px-10 py-8 flex justify-between items-start animate-fade-in">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="p-2 rounded-lg hover:bg-white/80 transition-colors"
              aria-label="Back to home"
            >
              <ArrowLeft className="w-6 h-6 text-stone-600" />
            </button>
            <div className="flex items-center gap-3">
              <div className="bg-[#2C2825] p-2.5 rounded-lg shadow-lg">
                <History className="w-6 h-6 text-[#F9F8F6]" />
              </div>
              <h1 className="text-4xl font-serif-display font-medium text-[#2C2825]">
                Session History
              </h1>
            </div>
          </div>
          <UserMenu />
        </header>

        <div className="flex-1 px-10 pb-10">
          {/* Filter Bar */}
          <div className="flex items-center gap-3 mb-6">
            <Filter className="w-4 h-4 text-stone-400" />
            <span className="text-sm text-stone-500 uppercase tracking-wider font-bold">
              Type:
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => handleFilterChange(null)}
                className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                  filter === null
                    ? 'bg-stone-800 text-white'
                    : 'bg-white/80 text-stone-600 hover:bg-white'
                }`}
              >
                All
              </button>
              <button
                onClick={() => handleFilterChange('training')}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                  filter === 'training'
                    ? 'bg-amber-600 text-white'
                    : 'bg-white/80 text-amber-700 hover:bg-white'
                }`}
              >
                <Dumbbell className="w-3 h-3" />
                Training
              </button>
              <button
                onClick={() => handleFilterChange('evaluation')}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                  filter === 'evaluation'
                    ? 'bg-red-600 text-white'
                    : 'bg-white/80 text-red-600 hover:bg-white'
                }`}
              >
                <Trophy className="w-3 h-3" />
                Evaluation
              </button>
            </div>
          </div>

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {/* Loading State */}
          {loading && sessions.length === 0 && (
            <div className="flex items-center justify-center py-20">
              <p className="text-stone-500 text-lg">Loading sessions...</p>
            </div>
          )}

          {/* Empty State */}
          {!loading && sessions.length === 0 && !error && (
            <div className="flex flex-col items-center justify-center py-20 opacity-50">
              <History className="w-20 h-20 text-stone-300 mb-4" />
              <p className="font-serif-display text-2xl text-stone-400 mb-2">
                No sessions yet
              </p>
              <p className="text-stone-500">
                Start your first training session to see your history here
              </p>
            </div>
          )}

          {/* Session Grid */}
          {sessions.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {sessions.map((session) => (
                <SessionCard
                  key={session.sessionId}
                  session={session}
                  onClick={handleSessionClick}
                />
              ))}
            </div>
          )}

          {/* Load More Button */}
          {hasMore && !loading && (
            <div className="flex justify-center mt-8">
              <button
                onClick={handleLoadMore}
                className="px-8 py-3 bg-white/80 backdrop-blur-md rounded-full border border-stone-200 shadow-sm hover:shadow-lg transition-all text-sm font-bold uppercase tracking-widest text-stone-700 hover:-translate-y-0.5"
              >
                Load More
              </button>
            </div>
          )}

          {/* Loading More Indicator */}
          {loading && sessions.length > 0 && (
            <div className="flex justify-center mt-8">
              <p className="text-stone-500">Loading more...</p>
            </div>
          )}
        </div>
      </div>

      {/* Session Detail Modal */}
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
