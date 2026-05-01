
export interface Message {
  id: string;
  role: 'user' | 'model' | 'system';
  text: string;
  timestamp: Date;
}

export enum ConnectionState {
  DISCONNECTED = 'DISCONNECTED',
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  ERROR = 'ERROR',
}

// Added SAFE_SPACE to resolve property missing errors in AmbientBackground.tsx
export enum AppMode {
  TRAINING = 'TRAINING',
  EVALUATION = 'EVALUATION',
  SAFE_SPACE = 'SAFE_SPACE'
}

export interface AudioVisualizerProps {
  analyser: AnalyserNode | null;
  isActive: boolean;
}

export interface LiveConfig {
  model: string;
  voiceName: string;
  systemInstruction?: string;
}

// --- PERSONA TYPES ---
export type Difficulty = 'high_regard' | 'medium_regard' | 'low_regard' | 'no_regard';

export interface Persona {
  id: string;
  name?: string; // Optional for evaluation personas
  backstory: string;
  looking_for?: string; // Optional for evaluation personas
  difficulty: Difficulty;
}

// --- EVALUATION TYPES ---
export type SalesStage = 'ENGAGE' | 'ASK' | 'SHOW' | 'YES' | 'COMPLETE';

export interface EvaluationState {
  currentStage: SalesStage;
  checklist: {
    engage: {
      nonBusinessGreet: boolean;
      establishedRapport: boolean;
      managerMention: boolean;
    };
    ask: {
      criticalQuestions: boolean;
      layer2Discovery: boolean;
      pbmsIdentified: boolean;
    };
    show: {
      powerDemo: boolean;
      featureBenefitPbm: boolean;
      protectionPlan: boolean;
    };
    yes: {
      payYourWay: boolean;
      clearConstraint: boolean;
      closedSale: boolean;
    };
  };
  feedback: string | null;
  finalReport?: string | null;
  cloudSyncStatus?: 'idle' | 'syncing' | 'synced' | 'error';
}

// --- COACH AGENT TYPES ---
export type InterventionLevel = 'info' | 'suggestion' | 'warning' | 'critical' | 'none';

export interface CoachHint {
  level: InterventionLevel;
  hint: string;
  stage: SalesStage;
  example_phrase: string | null;
  ready_for_next_stage: boolean;
  timestamp: Date;
}

// --- EVALUATION RESULT TYPES (from backend Evaluation model) ---
export type Grade = 'A' | 'B' | 'C' | 'D' | 'F';

export interface StageScore {
  stage: string;
  items_completed: string[];
  items_total: string[];
  score: number;
  weight: number;
  feedback: string | null;
}

export interface EvaluationScorecard {
  stage_scores: Record<string, StageScore>;
  pbm_match_rate: number;
  pbm_bonus: number;
  objection_resolution_rate: number;
  objection_penalty: number;
  deviations: string[];
  deviation_penalty: number;
  raw_score: number;
  final_score: number;
  grade: Grade;
}

export interface EvaluationResult {
  evaluation_id: string;
  session_id: string;
  scorecard: EvaluationScorecard;
  final_score: number;
  grade: Grade;
  summary: string | null;
  strengths: string[];
  improvements: string[];
  techniques_detected: string[];
}

// --- SESSION HISTORY TYPES ---
export type SessionType = 'training' | 'evaluation';
export type SessionStatus = 'active' | 'paused' | 'completed' | 'abandoned';

export interface SessionSummary {
  sessionId: string;
  sessionType: SessionType;
  status: SessionStatus;
  startedAt: string;
  endedAt: string | null;
  duration: number | null;
  selectedPersona: string | null;
  difficulty: Difficulty;
  messageCount: number;
  grade: Grade | null;
  score: number | null;
  hasEvaluation: boolean;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface SessionDetail {
  session: SessionSummary;
  transcript: {
    messages: Message[];
    totalMessages: number;
  };
  evaluation: EvaluationResult | null;
}
