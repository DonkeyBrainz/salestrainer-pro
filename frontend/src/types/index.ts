
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
  objections?: string[]; // Absent for evaluation personas (identity withheld)
}

// --- EVALUATION TYPES ---
export type SalesStage = 'CONNECT' | 'OBSERVE' | 'RECOMMEND' | 'EXECUTE' | 'COMPLETE';

export interface EvaluationState {
  currentStage: SalesStage;
  checklist: {
    connect: {
      warmGreeting: boolean;
      establishCredibility: boolean;
      createComfort: boolean;
    };
    observe: {
      needsDiscovery: boolean;
      goalIdentification: boolean;
      motivatorMapping: boolean;
    };
    recommend: {
      solutionPresentation: boolean;
      valueConnection: boolean;
      riskMitigation: boolean;
    };
    execute: {
      commitmentRequest: boolean;
      objectionHandling: boolean;
      finalizeAgreement: boolean;
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

// --- CUSTOMER MOOD TYPES ---
export type CustomerMood =
  | 'frustrated'
  | 'skeptical'
  | 'neutral'
  | 'interested'
  | 'ready_to_buy';

export type RegardLevel = 'high' | 'medium' | 'low' | 'no';

export interface CustomerMoodState {
  mood: CustomerMood;
  regard_level: RegardLevel;
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
  /** Subject identity was withheld during the live run; revealed once grading completes. */
  persona_name?: string | null;
}

// --- SESSION HISTORY TYPES ---
export type SessionType = 'training' | 'evaluation';
export type SessionStatus = 'active' | 'paused' | 'completed' | 'abandoned';

export interface SessionHint {
  t: string; // elapsed time offset, formatted MM:SS
  hint: string;
}

export interface SessionSummary {
  sessionId: string;
  sessionType: SessionType;
  status: SessionStatus;
  startedAt: string;
  endedAt: string | null;
  duration: number | null;
  selectedPersona: string | null;
  personaName: string | null;
  difficulty: Difficulty;
  messageCount: number;
  grade: Grade | null;
  score: number | null;
  hasEvaluation: boolean;
  hintsUsed: SessionHint[];
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
