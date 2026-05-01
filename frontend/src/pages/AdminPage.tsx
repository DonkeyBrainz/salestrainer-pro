import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { BarChart3, Users, MessageSquare, TrendingUp, AlertCircle, ArrowLeft, ChevronDown, ChevronRight, X } from 'lucide-react';
import SessionCard from '@/components/SessionCard';
import SessionDetailModal from '@/components/SessionDetailModal';
import type { SessionSummary } from '@/types';

interface PersonaMetrics {
  personaId: string;
  sessions: number;
  messageCount: number;
  volunteerScore: number;
  firstMessageVolunteerRate: number;
  salesModeViolations: number;
  volunteerCategories: Record<string, number>;
}

interface DifficultyMetrics {
  difficulty: string;
  sessions: number;
  messageCount: number;
  volunteerScore: number;
  firstMessageVolunteerRate: number;
}

interface PersonaMetricsResponse {
  totalSessions: number;
  totalTranscripts: number;
  byPersona: PersonaMetrics[];
  byDifficulty: DifficultyMetrics[];
}

interface UserMetrics {
  userId: string;
  userName: string;
  userEmail: string;
  totalSessions: number;
  totalTranscripts: number;
  totalMessages: number;
  avgMessagesPerSession: number;
  avgSessionDurationMinutes: number;
  sessionBreakdown: Record<string, number>;
  personaUsage: Record<string, number>;
  lastActive: string | null;
}

interface UserMetricsResponse {
  totalUsers: number;
  activeUsers7d: number;
  activeUsers30d: number;
  users: UserMetrics[];
}

const AdminPage: React.FC = () => {
  const { user, getValidToken } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'personas' | 'users'>('personas');
  const [personaMetrics, setPersonaMetrics] = useState<PersonaMetricsResponse | null>(null);
  const [userMetrics, setUserMetrics] = useState<UserMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // User session drill-down state
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);
  const [userSessions, setUserSessions] = useState<SessionSummary[]>([]);
  const [userSessionsLoading, setUserSessionsLoading] = useState(false);
  const [userSessionsTotal, setUserSessionsTotal] = useState(0);
  const [userSessionsOffset, setUserSessionsOffset] = useState(0);
  const [userSessionsHasMore, setUserSessionsHasMore] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const userSessionsLimit = 12;

  const fetchUserSessions = useCallback(async (userId: string, offset: number, append: boolean = false) => {
    try {
      setUserSessionsLoading(true);
      const token = await getValidToken();
      if (!token) return;

      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const params = new URLSearchParams({
        limit: userSessionsLimit.toString(),
        offset: offset.toString(),
      });

      const res = await fetch(`${apiBase}/api/v1/admin/users/${userId}/sessions?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!res.ok) return;

      const data = await res.json();
      const sessions: SessionSummary[] = data.sessions.map((s: any) => ({
        sessionId: s.session_id,
        sessionType: s.session_type,
        status: s.status,
        startedAt: s.started_at,
        endedAt: s.ended_at,
        duration: s.duration,
        selectedPersona: s.selected_persona,
        difficulty: s.difficulty,
        messageCount: s.message_count ?? 0,
        grade: s.grade,
        score: s.score,
        hasEvaluation: s.has_evaluation ?? false,
      }));

      if (append) {
        setUserSessions(prev => [...prev, ...sessions]);
      } else {
        setUserSessions(sessions);
      }
      setUserSessionsOffset(offset);
      setUserSessionsTotal(data.total);
      setUserSessionsHasMore(data.has_more);
    } finally {
      setUserSessionsLoading(false);
    }
  }, [getValidToken]);

  const handleUserClick = (userId: string) => {
    if (expandedUserId === userId) {
      setExpandedUserId(null);
      setUserSessions([]);
      return;
    }
    setExpandedUserId(userId);
    setUserSessionsOffset(0);
    fetchUserSessions(userId, 0);
  };

  const handleUserSessionLoadMore = () => {
    if (!expandedUserId) return;
    fetchUserSessions(expandedUserId, userSessionsOffset + userSessionsLimit, true);
  };

  const handleSessionClick = (sessionId: string) => {
    setSelectedSessionId(sessionId);
  };

  const handleCloseSessionModal = () => {
    setSelectedSessionId(null);
  };

  const handleFetchSession = useCallback(async (sessionId: string) => {
    const token = await getValidToken();
    if (!token) throw new Error('Not authenticated');

    const apiBase = import.meta.env.VITE_API_BASE_URL || '';
    const res = await fetch(`${apiBase}/api/v1/admin/sessions/${sessionId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!res.ok) {
      if (res.status === 404) throw new Error('Session not found');
      throw new Error('Failed to fetch session');
    }

    const data = await res.json();

    return {
      session: {
        sessionId: data.session.session_id,
        sessionType: data.session.session_type,
        status: data.session.status,
        startedAt: data.session.started_at,
        endedAt: data.session.ended_at,
        duration: data.session.duration,
        selectedPersona: data.session.selected_persona,
        difficulty: data.session.difficulty,
        messageCount: data.session.message_count,
        grade: data.session.grade,
        score: data.session.score,
        hasEvaluation: data.session.has_evaluation,
      },
      transcript: {
        messages: data.transcript.messages.map((msg: any) => ({
          id: msg.message_id,
          role: msg.role,
          text: msg.text,
          timestamp: new Date(msg.timestamp),
        })),
        totalMessages: data.transcript.total_messages,
      },
      evaluation: data.evaluation ? {
        evaluation_id: data.evaluation.evaluation_id,
        session_id: data.evaluation.session_id,
        scorecard: data.evaluation.scorecard,
        final_score: data.evaluation.final_score,
        grade: data.evaluation.grade,
        summary: data.evaluation.summary,
        strengths: data.evaluation.strengths,
        improvements: data.evaluation.improvements,
        techniques_detected: data.evaluation.techniques_detected,
      } : null,
    };
  }, [getValidToken]);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        setError(null);

        const token = await getValidToken();
        if (!token) {
          setError('Not authenticated');
          return;
        }

        const headers = {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        };

        const apiBase = import.meta.env.VITE_API_BASE_URL || '';

        // Fetch both persona and user metrics
        const [personaRes, userRes] = await Promise.all([
          fetch(`${apiBase}/api/v1/admin/personas/metrics`, { headers, credentials: 'include' }),
          fetch(`${apiBase}/api/v1/admin/users/metrics`, { headers, credentials: 'include' }),
        ]);

        if (!personaRes.ok || !userRes.ok) {
          if (personaRes.status === 403 || userRes.status === 403) {
            setError('Admin access required');
          } else {
            setError('Failed to fetch metrics');
          }
          return;
        }

        const personaData = await personaRes.json();
        const userData = await userRes.json();

        setPersonaMetrics(personaData);
        setUserMetrics(userData);
      } catch (err) {
        console.error('Error fetching metrics:', err);
        setError('Failed to load admin metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [getValidToken]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-stone-50 to-amber-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#8B5E3C]"></div>
          <p className="mt-4 text-stone-600">Loading admin metrics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-stone-50 to-amber-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-serif-display text-[#2C2825] mb-2">Access Denied</h2>
          <p className="text-stone-600 mb-6">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-[#8B5E3C] hover:bg-[#6D4A2E] text-white rounded-full font-bold uppercase tracking-wider transition-colors"
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  const getDifficultyLabel = (diff: string) => {
    const labels: Record<string, string> = {
      'high_regard': 'High Regard',
      'medium_regard': 'Medium Regard',
      'low_regard': 'Low Regard',
      'no_regard': 'No Regard',
      'easy': 'High Regard (Legacy)',
      'medium': 'Medium (Legacy)',
      'hard': 'Hard (Legacy)',
    };
    return labels[diff] || diff;
  };

  const getVolunteerScoreColor = (score: number) => {
    if (score > 1.0) return 'text-emerald-600 bg-emerald-50';
    if (score > 0.5) return 'text-amber-600 bg-amber-50';
    return 'text-red-600 bg-red-50';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 to-amber-50">
      {/* Header */}
      <div className="bg-white border-b border-stone-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/')}
                className="p-2 hover:bg-stone-100 rounded-full transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-stone-600" />
              </button>
              <div>
                <h1 className="text-2xl font-serif-display text-[#2C2825]">Admin Dashboard</h1>
                <p className="text-sm text-stone-500">System metrics and analytics</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-stone-600">{user?.name}</p>
              <p className="text-xs text-stone-400">{user?.email}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('personas')}
            className={`px-6 py-3 rounded-full font-bold uppercase tracking-wider text-sm transition-colors ${
              activeTab === 'personas'
                ? 'bg-[#8B5E3C] text-white'
                : 'bg-white text-stone-600 hover:bg-stone-100'
            }`}
          >
            <BarChart3 className="inline-block w-4 h-4 mr-2" />
            Persona Metrics
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-6 py-3 rounded-full font-bold uppercase tracking-wider text-sm transition-colors ${
              activeTab === 'users'
                ? 'bg-[#8B5E3C] text-white'
                : 'bg-white text-stone-600 hover:bg-stone-100'
            }`}
          >
            <Users className="inline-block w-4 h-4 mr-2" />
            User Metrics
          </button>
        </div>

        {/* Persona Metrics Tab */}
        {activeTab === 'personas' && personaMetrics && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white rounded-xl p-6 border border-stone-200">
                <div className="flex items-center gap-3 mb-2">
                  <MessageSquare className="w-5 h-5 text-[#8B5E3C]" />
                  <h3 className="font-bold text-stone-800">Total Sessions</h3>
                </div>
                <p className="text-3xl font-serif-display text-[#2C2825]">{personaMetrics.totalSessions}</p>
              </div>
              <div className="bg-white rounded-xl p-6 border border-stone-200">
                <div className="flex items-center gap-3 mb-2">
                  <TrendingUp className="w-5 h-5 text-[#8B5E3C]" />
                  <h3 className="font-bold text-stone-800">Total Transcripts</h3>
                </div>
                <p className="text-3xl font-serif-display text-[#2C2825]">{personaMetrics.totalTranscripts}</p>
              </div>
            </div>

            {/* By Difficulty */}
            <div className="bg-white rounded-xl p-6 border border-stone-200">
              <h2 className="text-xl font-serif-display text-[#2C2825] mb-4">Volunteer Scores by Difficulty</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left py-3 px-4 text-sm font-bold text-stone-600">Difficulty</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Sessions</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Messages</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Volunteer Score</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">1st Msg Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {personaMetrics.byDifficulty.map((diff) => (
                      <tr key={diff.difficulty} className="border-b border-stone-100 hover:bg-stone-50">
                        <td className="py-3 px-4 font-medium">{getDifficultyLabel(diff.difficulty)}</td>
                        <td className="py-3 px-4 text-right">{diff.sessions}</td>
                        <td className="py-3 px-4 text-right">{diff.messageCount}</td>
                        <td className="py-3 px-4 text-right">
                          <span className={`px-2 py-1 rounded text-sm font-bold ${getVolunteerScoreColor(diff.volunteerScore)}`}>
                            {diff.volunteerScore.toFixed(2)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">{diff.firstMessageVolunteerRate.toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* By Persona */}
            <div className="bg-white rounded-xl p-6 border border-stone-200">
              <h2 className="text-xl font-serif-display text-[#2C2825] mb-4">Persona Performance</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left py-3 px-4 text-sm font-bold text-stone-600">Persona</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Sessions</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Messages</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Volunteer Score</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">1st Msg Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {personaMetrics.byPersona.map((persona) => (
                      <tr key={persona.personaId} className="border-b border-stone-100 hover:bg-stone-50">
                        <td className="py-3 px-4 font-medium capitalize">{persona.personaId.replace(/_/g, ' ')}</td>
                        <td className="py-3 px-4 text-right">{persona.sessions}</td>
                        <td className="py-3 px-4 text-right">{persona.messageCount}</td>
                        <td className="py-3 px-4 text-right">
                          <span className={`px-2 py-1 rounded text-sm font-bold ${getVolunteerScoreColor(persona.volunteerScore)}`}>
                            {persona.volunteerScore.toFixed(2)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">{persona.firstMessageVolunteerRate.toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* User Metrics Tab */}
        {activeTab === 'users' && userMetrics && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-xl p-6 border border-stone-200">
                <div className="flex items-center gap-3 mb-2">
                  <Users className="w-5 h-5 text-[#8B5E3C]" />
                  <h3 className="font-bold text-stone-800">Total Users</h3>
                </div>
                <p className="text-3xl font-serif-display text-[#2C2825]">{userMetrics.totalUsers}</p>
              </div>
              <div className="bg-white rounded-xl p-6 border border-stone-200">
                <div className="flex items-center gap-3 mb-2">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                  <h3 className="font-bold text-stone-800">Active (7d)</h3>
                </div>
                <p className="text-3xl font-serif-display text-[#2C2825]">{userMetrics.activeUsers7d}</p>
              </div>
              <div className="bg-white rounded-xl p-6 border border-stone-200">
                <div className="flex items-center gap-3 mb-2">
                  <TrendingUp className="w-5 h-5 text-amber-600" />
                  <h3 className="font-bold text-stone-800">Active (30d)</h3>
                </div>
                <p className="text-3xl font-serif-display text-[#2C2825]">{userMetrics.activeUsers30d}</p>
              </div>
            </div>

            {/* User Table */}
            <div className="bg-white rounded-xl p-6 border border-stone-200">
              <h2 className="text-xl font-serif-display text-[#2C2825] mb-4">User Activity</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left py-3 px-4 text-sm font-bold text-stone-600">User</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Sessions</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Transcripts</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Avg Msgs</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Avg Duration</th>
                      <th className="text-right py-3 px-4 text-sm font-bold text-stone-600">Last Active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {userMetrics.users.map((u) => (
                      <React.Fragment key={u.userId}>
                        <tr
                          onClick={() => handleUserClick(u.userId)}
                          className="border-b border-stone-100 hover:bg-stone-50 cursor-pointer transition-colors"
                        >
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              {expandedUserId === u.userId
                                ? <ChevronDown className="w-4 h-4 text-stone-400 flex-shrink-0" />
                                : <ChevronRight className="w-4 h-4 text-stone-400 flex-shrink-0" />}
                              <div>
                                <p className="font-medium">{u.userName}</p>
                                <p className="text-xs text-stone-500">{u.userEmail}</p>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-4 text-right">{u.totalSessions}</td>
                          <td className="py-3 px-4 text-right">{u.totalTranscripts}</td>
                          <td className="py-3 px-4 text-right">{u.avgMessagesPerSession.toFixed(1)}</td>
                          <td className="py-3 px-4 text-right">{u.avgSessionDurationMinutes.toFixed(1)}m</td>
                          <td className="py-3 px-4 text-right text-sm text-stone-500">
                            {u.lastActive ? new Date(u.lastActive).toLocaleDateString() : 'Never'}
                          </td>
                        </tr>
                        {expandedUserId === u.userId && (
                          <tr>
                            <td colSpan={6} className="p-0">
                              <div className="bg-stone-50 border-t border-stone-200 px-6 py-4">
                                <div className="flex items-center justify-between mb-4">
                                  <h3 className="text-sm font-bold uppercase tracking-wider text-stone-600">
                                    Sessions for {u.userName} ({userSessionsTotal})
                                  </h3>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); setExpandedUserId(null); setUserSessions([]); }}
                                    className="p-1 hover:bg-stone-200 rounded transition-colors"
                                  >
                                    <X className="w-4 h-4 text-stone-400" />
                                  </button>
                                </div>
                                {userSessionsLoading && userSessions.length === 0 ? (
                                  <p className="text-stone-500 text-sm py-4 text-center">Loading sessions...</p>
                                ) : userSessions.length === 0 ? (
                                  <p className="text-stone-400 text-sm py-4 text-center">No sessions found</p>
                                ) : (
                                  <>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                      {userSessions.map((session) => (
                                        <SessionCard
                                          key={session.sessionId}
                                          session={session}
                                          onClick={handleSessionClick}
                                        />
                                      ))}
                                    </div>
                                    {userSessionsHasMore && !userSessionsLoading && (
                                      <div className="flex justify-center mt-4">
                                        <button
                                          onClick={(e) => { e.stopPropagation(); handleUserSessionLoadMore(); }}
                                          className="px-6 py-2 bg-white rounded-full border border-stone-200 shadow-sm hover:shadow-md transition-all text-xs font-bold uppercase tracking-widest text-stone-600"
                                        >
                                          Load More
                                        </button>
                                      </div>
                                    )}
                                    {userSessionsLoading && userSessions.length > 0 && (
                                      <p className="text-stone-500 text-sm py-4 text-center">Loading more...</p>
                                    )}
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Session Detail Modal */}
      {selectedSessionId && (
        <SessionDetailModal
          sessionId={selectedSessionId}
          onClose={handleCloseSessionModal}
          onFetchSession={handleFetchSession}
        />
      )}
    </div>
  );
};

export default AdminPage;
