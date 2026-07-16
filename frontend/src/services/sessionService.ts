import type { SessionListResponse, SessionDetail, SessionType } from '@/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

interface SessionListParams {
  limit?: number;
  offset?: number;
  sessionType?: SessionType;
}

class SessionService {
  private static instance: SessionService;

  static getInstance(): SessionService {
    if (!SessionService.instance) {
      SessionService.instance = new SessionService();
    }
    return SessionService.instance;
  }

  async listSessions(
    accessToken: string,
    params: SessionListParams = {}
  ): Promise<SessionListResponse> {
    const { limit = 20, offset = 0, sessionType } = params;

    const queryParams = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

    if (sessionType) {
      queryParams.append('session_type', sessionType);
    }

    const response = await fetch(`${API_BASE}/api/v1/sessions?${queryParams}`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: { message: 'Failed to fetch sessions' } }));
      throw new Error(error.error?.message || 'Failed to fetch sessions');
    }

    const data = await response.json();

    // Convert snake_case to camelCase
    return {
      ...data,
      sessions: data.sessions.map((session: any) => ({
        ...session,
        startedAt: session.startedAt || session.started_at,
        endedAt: session.endedAt || session.ended_at,
        sessionId: session.sessionId || session.session_id,
        sessionType: session.sessionType || session.session_type,
        selectedPersona: session.selectedPersona || session.selected_persona,
        personaName: session.personaName ?? session.persona_name ?? null,
        messageCount: session.messageCount ?? session.message_count ?? 0,
        hasEvaluation: session.hasEvaluation ?? session.has_evaluation ?? false,
        hintsUsed: session.hintsUsed ?? session.hints_used ?? [],
        grade: session.grade,
        score: session.score,
      })),
    };
  }

  async getSessionDetail(
    accessToken: string,
    sessionId: string
  ): Promise<SessionDetail> {
    const response = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Session not found');
      }
      if (response.status === 403) {
        throw new Error('Access denied to this session');
      }
      const error = await response.json().catch(() => ({ error: { message: 'Failed to fetch session' } }));
      throw new Error(error.error?.message || 'Failed to fetch session');
    }

    const data = await response.json();

    // Convert snake_case to camelCase and parse dates
    return {
      session: {
        sessionId: data.session.session_id,
        sessionType: data.session.session_type,
        status: data.session.status,
        startedAt: data.session.started_at,
        endedAt: data.session.ended_at,
        duration: data.session.duration,
        selectedPersona: data.session.selected_persona,
        personaName: data.session.persona_name ?? null,
        difficulty: data.session.difficulty,
        messageCount: data.session.message_count,
        grade: data.session.grade,
        score: data.session.score,
        hasEvaluation: data.session.has_evaluation,
        hintsUsed: data.session.hints_used ?? [],
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
  }
}

export const sessionService = SessionService.getInstance();
