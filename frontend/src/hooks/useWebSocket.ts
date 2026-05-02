import { useState, useEffect, useCallback, useRef } from 'react';
import { ConnectionState, Message, CoachHint, EvaluationResult, SalesStage } from '@/types';
import { useAuth } from '@/contexts/AuthContext';
import {
  websocketService,
  ServerMessage,
  TranscriptionMessage,
  ServerAudioMessage,
  CoachHintMessage,
  StageProgressMessage,
  UserTranscriptionMessage,
  EvaluationResultMessage,
  EvaluationErrorMessage,
} from '@/services/websocketService';

export interface UseWebSocketReturn {
  connectionState: ConnectionState;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  connect: (personaId?: string, mode?: 'training' | 'evaluation', productCategory?: string, productType?: string) => Promise<void>;
  disconnect: () => void;
  sendAudio: (base64Data: string) => void;
  sendText: (content: string) => void;
  sendControl: (action: 'end_turn' | 'evaluate') => void;
  messages: Message[];
  currentInput: string;
  onAudioReceived: React.MutableRefObject<((base64Pcm: string) => void) | null>;
  currentHint: CoachHint | null;
  completedItems: string[];
  currentStage: SalesStage;
  userTranscription: string;
  dismissHint: () => void;
  recallHint: () => void;
  evaluationResult: EvaluationResult | null;
  isEvaluating: boolean;
  requestEvaluation: () => void;
  clearEvaluation: () => void;
}

function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

export function useWebSocket(): UseWebSocketReturn {
  const { getValidToken } = useAuth();
  const [connectionState, setConnectionState] = useState<ConnectionState>(
    websocketService.getState()
  );
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentInput, setCurrentInput] = useState('');
  const [currentHint, setCurrentHint] = useState<CoachHint | null>(null);
  const [dismissedHint, setDismissedHint] = useState<CoachHint | null>(null);
  const [userTranscription, setUserTranscription] = useState<string>('');
  const [completedItems, setCompletedItems] = useState<string[]>([]);
  const [currentStage, setCurrentStage] = useState<SalesStage>('CONNECT');
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResult | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);

  // Ref for audio callback to allow integration with useAudio
  const onAudioReceived = useRef<((base64Pcm: string) => void) | null>(null);

  // Refs for accumulating transcription chunks within a turn
  const pendingUserText = useRef('');
  const pendingAssistantText = useRef('');

  // Set up token provider on mount
  useEffect(() => {
    websocketService.setTokenProvider(getValidToken);
  }, [getValidToken]);

  // Subscribe to state changes
  useEffect(() => {
    const unsubscribe = websocketService.onStateChange((newState) => {
      setConnectionState(newState);
      if (newState === ConnectionState.ERROR) {
        setError('Connection error');
      } else if (newState === ConnectionState.CONNECTED) {
        setError(null);
      }
    });

    return unsubscribe;
  }, []);

  // Subscribe to messages
  useEffect(() => {
    const unsubscribe = websocketService.onMessage((message: ServerMessage) => {
      switch (message.type) {
        case 'transcription': {
          // Accumulate assistant speech chunks (backend sends without role/isFinal)
          const txMsg = message as TranscriptionMessage;
          if (txMsg.text) {
            pendingAssistantText.current += txMsg.text;
          }
          break;
        }

        case 'audio':
          handleAudio(message);
          break;

        case 'coach_hint': {
          const coachMessage = message as CoachHintMessage;
          const hint: CoachHint = {
            level: coachMessage.level,
            hint: coachMessage.hint,
            stage: coachMessage.stage,
            example_phrase: coachMessage.example_phrase,
            ready_for_next_stage: coachMessage.ready_for_next_stage,
            timestamp: new Date(),
          };
          setCurrentHint(hint);
          break;
        }

        case 'stage_progress': {
          const progressMsg = message as StageProgressMessage;
          setCompletedItems(progressMsg.all_completed_items);
          setCurrentStage(progressMsg.current_stage);
          break;
        }

        case 'user_transcription': {
          const transcriptionMessage = message as UserTranscriptionMessage;
          pendingUserText.current += transcriptionMessage.text;
          setUserTranscription((prev) => prev + transcriptionMessage.text);
          break;
        }

        case 'turn_complete': {
          // Flush accumulated transcriptions into messages
          const userText = pendingUserText.current.trim();
          const assistantText = pendingAssistantText.current.trim();

          if (userText) {
            setMessages((prev) => [
              ...prev,
              {
                id: generateMessageId(),
                role: 'user',
                text: userText,
                timestamp: new Date(),
              },
            ]);
          }
          if (assistantText) {
            setMessages((prev) => [
              ...prev,
              {
                id: generateMessageId(),
                role: 'model',
                text: assistantText,
                timestamp: new Date(),
              },
            ]);
          }

          // Reset accumulators and partial UI state
          pendingUserText.current = '';
          pendingAssistantText.current = '';
          setCurrentInput('');
          setUserTranscription('');
          break;
        }

        case 'reconnecting':
          // Backend is reconnecting to Gemini - session continues transparently
          console.log('Session reconnecting to AI...');
          break;

        case 'session_resumed':
          // Backend successfully resumed session with Gemini
          console.log('Session resumed successfully');
          break;

        case 'evaluation_result': {
          const evalMsg = message as EvaluationResultMessage;
          setEvaluationResult(evalMsg.evaluation);
          setIsEvaluating(false);
          break;
        }

        case 'evaluation_error': {
          const evalErrMsg = message as EvaluationErrorMessage;
          setError(evalErrMsg.message);
          setIsEvaluating(false);
          break;
        }

        case 'error':
          setError(`${message.code}: ${message.message}`);
          break;

        default:
          break;
      }
    });

    return unsubscribe;
  }, []);

  const handleAudio = useCallback((message: ServerAudioMessage) => {
    if (onAudioReceived.current) {
      onAudioReceived.current(message.data);
    }
  }, []);

  const connect = useCallback(async (personaId?: string, mode: 'training' | 'evaluation' = 'training', productCategory?: string, productType?: string) => {
    setError(null);
    try {
      await websocketService.connect(personaId, mode, productCategory, productType);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Connection failed';
      setError(errorMessage);
      throw err;
    }
  }, []);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setMessages([]);
    setCurrentInput('');
    setError(null);
    setCompletedItems([]);
    setCurrentStage('CONNECT');
  }, []);

  const sendAudio = useCallback((base64Data: string) => {
    websocketService.sendAudio(base64Data);
  }, []);

  const sendText = useCallback((content: string) => {
    websocketService.sendText(content);
  }, []);

  const sendControl = useCallback((action: 'end_turn' | 'evaluate') => {
    websocketService.sendControl(action);
  }, []);

  const dismissHint = useCallback(() => {
    setDismissedHint(currentHint);
    setCurrentHint(null);
  }, [currentHint]);

  const recallHint = useCallback(() => {
    if (dismissedHint && !currentHint) {
      setCurrentHint(dismissedHint);
    }
  }, [dismissedHint, currentHint]);

  const requestEvaluation = useCallback(() => {
    // Flush any pending transcription chunks before evaluating
    const userText = pendingUserText.current.trim();
    const assistantText = pendingAssistantText.current.trim();
    if (userText) {
      setMessages((prev) => [
        ...prev,
        { id: generateMessageId(), role: 'user', text: userText, timestamp: new Date() },
      ]);
    }
    if (assistantText) {
      setMessages((prev) => [
        ...prev,
        { id: generateMessageId(), role: 'model', text: assistantText, timestamp: new Date() },
      ]);
    }
    pendingUserText.current = '';
    pendingAssistantText.current = '';

    setIsEvaluating(true);
    websocketService.sendControl('evaluate');
  }, []);

  const clearEvaluation = useCallback(() => {
    setEvaluationResult(null);
  }, []);

  return {
    connectionState,
    isConnected: connectionState === ConnectionState.CONNECTED,
    isConnecting: connectionState === ConnectionState.CONNECTING,
    error,
    connect,
    disconnect,
    sendAudio,
    sendText,
    sendControl,
    messages,
    currentInput,
    onAudioReceived,
    currentHint,
    completedItems,
    currentStage,
    userTranscription,
    dismissHint,
    recallHint,
    evaluationResult,
    isEvaluating,
    requestEvaluation,
    clearEvaluation,
  };
}
