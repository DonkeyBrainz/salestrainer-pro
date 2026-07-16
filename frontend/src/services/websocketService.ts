import { ConnectionState, CustomerMood, EvaluationResult } from '@/types';
import { logger } from './logger';
import { base64ToBytes, bytesToBase64 } from './audioUtils';

// ============================================================================
// Message Types
// ============================================================================

// Client -> Server
export interface AudioMessage {
  type: 'audio';
  data: string;
  sampleRate: 16000;
}

export interface TextMessage {
  type: 'text';
  content: string;
}

export interface ControlMessage {
  type: 'control';
  action: 'end_turn' | 'evaluate';
}

export type ClientMessage = AudioMessage | TextMessage | ControlMessage;

// Server -> Client
export interface ReadyMessage {
  type: 'ready';
}

export interface ServerAudioMessage {
  type: 'audio';
  data: string;
  sampleRate: 24000;
}

export interface TranscriptionMessage {
  type: 'transcription';
  role: 'user' | 'model';
  text: string;
  isFinal: boolean;
}

export interface TurnCompleteMessage {
  type: 'turn_complete';
}

export interface ErrorMessage {
  type: 'error';
  code: string;
  message: string;
}

export interface CoachHintMessage {
  type: 'coach_hint';
  level: 'info' | 'suggestion' | 'warning' | 'critical' | 'none';
  hint: string;
  stage: 'CONNECT' | 'OBSERVE' | 'RECOMMEND' | 'EXECUTE' | 'COMPLETE';
  example_phrase: string | null;
  ready_for_next_stage: boolean;
}

export interface UserTranscriptionMessage {
  type: 'user_transcription';
  text: string;
}

export interface ReconnectingMessage {
  type: 'reconnecting';
}

export interface SessionResumedMessage {
  type: 'session_resumed';
}

export interface EvaluationResultMessage {
  type: 'evaluation_result';
  evaluation: EvaluationResult;
  persona_name?: string | null;
}

export interface EvaluationErrorMessage {
  type: 'evaluation_error';
  message: string;
}

export interface StageProgressMessage {
  type: 'stage_progress';
  current_stage: 'CONNECT' | 'OBSERVE' | 'RECOMMEND' | 'EXECUTE' | 'COMPLETE';
  all_completed_items: string[];
}

export interface MoodUpdateMessage {
  type: 'mood_update';
  mood: CustomerMood;
  regard_level: 'high' | 'medium' | 'low' | 'no';
}

export type ServerMessage =
  | ReadyMessage
  | ServerAudioMessage
  | TranscriptionMessage
  | TurnCompleteMessage
  | ErrorMessage
  | CoachHintMessage
  | MoodUpdateMessage
  | UserTranscriptionMessage
  | ReconnectingMessage
  | SessionResumedMessage
  | EvaluationResultMessage
  | EvaluationErrorMessage
  | StageProgressMessage;

// ============================================================================
// WebSocket Error Codes
// ============================================================================

export const WS_CLOSE_CODES = {
  NORMAL: 1000,
  AUTH_FAILED: 4001,
  SESSION_LIMIT: 4002,
  RATE_LIMIT: 4003,
  INVALID_MESSAGE: 4004,
  GEMINI_FAILED: 4005,
} as const;

// ============================================================================
// Types
// ============================================================================

export type TokenProvider = () => Promise<string | null>;
export type StateChangeListener = (state: ConnectionState) => void;
export type MessageListener = (message: ServerMessage) => void;

interface ReconnectConfig {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
}

// ============================================================================
// WebSocketService Singleton
// ============================================================================

class WebSocketService {
  private ws: WebSocket | null = null;
  private tokenProvider: TokenProvider | null = null;
  private state: ConnectionState = ConnectionState.DISCONNECTED;
  private stateListeners = new Set<StateChangeListener>();
  private messageListeners = new Set<MessageListener>();
  private reconnectAttempts = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = false;
  private currentPersonaId: string | null = null;
  private currentProductCategory: string | null = null;
  private currentProductType: string | null = null;

  private readonly reconnectConfig: ReconnectConfig = {
    maxAttempts: 5,
    baseDelayMs: 1000,
    maxDelayMs: 30000,
  };

  private getWsUrl(mode: 'training' | 'evaluation' = 'training'): string {
    const apiBase = import.meta.env.VITE_API_BASE_URL || '';

    if (apiBase) {
      // Production: use backend URL
      const wsUrl = apiBase.replace(/^http/, 'ws');
      return `${wsUrl}/ws/gemini/live?mode=${encodeURIComponent(mode)}`;
    } else {
      // Development: use relative URL (Vite proxy)
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      return `${protocol}//${host}/ws/gemini/live?mode=${encodeURIComponent(mode)}`;
    }
  }

  setTokenProvider(provider: TokenProvider): void {
    this.tokenProvider = provider;
  }

  getState(): ConnectionState {
    return this.state;
  }

  private setState(newState: ConnectionState): void {
    if (this.state !== newState) {
      this.state = newState;
      logger.info('Network', `WebSocket state: ${newState}`);
      this.stateListeners.forEach((listener) => listener(newState));
    }
  }

  onStateChange(listener: StateChangeListener): () => void {
    this.stateListeners.add(listener);
    return () => {
      this.stateListeners.delete(listener);
    };
  }

  onMessage(listener: MessageListener): () => void {
    this.messageListeners.add(listener);
    return () => {
      this.messageListeners.delete(listener);
    };
  }

  async connect(personaId?: string, mode: 'training' | 'evaluation' = 'training', productCategory?: string, productType?: string): Promise<void> {
    if (this.state === ConnectionState.CONNECTING || this.state === ConnectionState.CONNECTED) {
      logger.warn('Network', 'WebSocket already connecting or connected');
      return;
    }

    if (!this.tokenProvider) {
      throw new Error('Token provider not set. Call setTokenProvider first.');
    }

    const token = await this.tokenProvider();
    if (!token) {
      this.setState(ConnectionState.ERROR);
      throw new Error('Failed to obtain authentication token');
    }

    // Store persona ID and product selection for reconnection
    if (personaId) {
      this.currentPersonaId = personaId;
    }
    if (productCategory !== undefined) {
      this.currentProductCategory = productCategory ?? null;
    }
    if (productType !== undefined) {
      this.currentProductType = productType ?? null;
    }

    this.shouldReconnect = true;
    this.setState(ConnectionState.CONNECTING);

    // Include persona_id for customer agent
    const effectivePersonaId = this.currentPersonaId || 'eager_newlywed';
    let url = `${this.getWsUrl(mode)}&token=${encodeURIComponent(token)}&persona_id=${encodeURIComponent(effectivePersonaId)}`;

    if (this.currentProductCategory) {
      url += `&product_category=${encodeURIComponent(this.currentProductCategory)}`;
    }
    if (this.currentProductType) {
      url += `&product_type=${encodeURIComponent(this.currentProductType)}`;
    }

    return new Promise<void>((resolve, reject) => {
      try {
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          logger.info('Network', 'WebSocket connected');
          this.reconnectAttempts = 0;
          // State set to CONNECTED after receiving 'ready' message
        };

        this.ws.onmessage = async (event: MessageEvent) => {
          try {
            // Handle binary audio data from server
            if (event.data instanceof Blob) {
              const arrayBuffer = await event.data.arrayBuffer();
              const uint8Array = new Uint8Array(arrayBuffer);
              // Convert to base64 for the audio hook
              const base64 = bytesToBase64(uint8Array);
              const audioMessage: ServerAudioMessage = {
                type: 'audio',
                data: base64,
                sampleRate: 24000,
              };
              this.handleMessage(audioMessage);
              return;
            }

            // Handle JSON messages
            const message = JSON.parse(event.data) as ServerMessage;
            this.handleMessage(message);

            // Resolve promise on ready message
            if (message.type === 'ready') {
              resolve();
            }
          } catch (err) {
            logger.error('Network', 'Failed to parse WebSocket message', { error: err });
          }
        };

        this.ws.onerror = (event: Event) => {
          logger.error('Network', 'WebSocket error', { event });
          this.setState(ConnectionState.ERROR);
          reject(new Error('WebSocket connection error'));
        };

        this.ws.onclose = (event: CloseEvent) => {
          this.handleClose(event);
          if (this.state === ConnectionState.CONNECTING) {
            reject(new Error(`WebSocket closed during connection: ${event.code}`));
          }
        };
      } catch (err) {
        this.setState(ConnectionState.ERROR);
        reject(err);
      }
    });
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.clearReconnectTimeout();
    this.currentPersonaId = null;
    this.currentProductCategory = null;
    this.currentProductType = null;

    if (this.ws) {
      this.ws.onclose = null; // Prevent reconnect logic
      this.ws.close(WS_CLOSE_CODES.NORMAL, 'Client disconnect');
      this.ws = null;
    }

    this.setState(ConnectionState.DISCONNECTED);
    logger.info('Network', 'WebSocket disconnected by client');
  }

  private handleMessage(message: ServerMessage): void {
    switch (message.type) {
      case 'ready':
        this.setState(ConnectionState.CONNECTED);
        logger.info('Network', 'Gemini connection ready');
        break;

      case 'error':
        logger.error('Network', `Server error: ${message.code} - ${message.message}`);
        break;

      default:
        // Pass through to listeners
        break;
    }

    this.messageListeners.forEach((listener) => listener(message));
  }

  private handleClose(event: CloseEvent): void {
    this.ws = null;
    logger.info('Network', `WebSocket closed: ${event.code} - ${event.reason}`);

    // Handle specific close codes
    switch (event.code) {
      case WS_CLOSE_CODES.AUTH_FAILED:
        this.setState(ConnectionState.ERROR);
        logger.error('Network', 'Authentication failed');
        return; // Don't reconnect on auth failure

      case WS_CLOSE_CODES.RATE_LIMIT:
        this.setState(ConnectionState.ERROR);
        logger.warn('Network', 'Rate limit exceeded');
        return; // Don't reconnect on rate limit

      case WS_CLOSE_CODES.SESSION_LIMIT:
        this.setState(ConnectionState.ERROR);
        logger.warn('Network', 'Session limit exceeded');
        return; // Don't reconnect on session limit

      case WS_CLOSE_CODES.INVALID_MESSAGE:
        logger.warn('Network', 'Invalid message format');
        break;

      case WS_CLOSE_CODES.GEMINI_FAILED:
        logger.error('Network', 'Gemini connection failed');
        break;

      case WS_CLOSE_CODES.NORMAL:
        this.setState(ConnectionState.DISCONNECTED);
        return; // Normal close, don't reconnect
    }

    // Attempt reconnection for recoverable errors
    if (this.shouldReconnect) {
      this.scheduleReconnect();
    } else {
      this.setState(ConnectionState.DISCONNECTED);
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.reconnectConfig.maxAttempts) {
      logger.error('Network', 'Max reconnection attempts reached');
      this.setState(ConnectionState.ERROR);
      this.shouldReconnect = false;
      return;
    }

    const delay = Math.min(
      this.reconnectConfig.baseDelayMs * Math.pow(2, this.reconnectAttempts),
      this.reconnectConfig.maxDelayMs
    );

    this.reconnectAttempts++;
    logger.info('Network', `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    // Set to DISCONNECTED so connect() guard doesn't block when timeout fires
    this.setState(ConnectionState.DISCONNECTED);

    this.reconnectTimeout = setTimeout(() => {
      this.connect().catch((err) => {
        logger.error('Network', 'Reconnection failed', { error: err });
      });
    }, delay);
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  // ============================================================================
  // Send Methods
  // ============================================================================

  sendAudio(base64Data: string): void {
    if (!this.isConnected()) {
      logger.warn('Network', 'Cannot send audio: not connected');
      return;
    }

    // Send as binary data (backend expects raw PCM bytes)
    const binaryData = base64ToBytes(base64Data);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(binaryData);
    }
  }

  sendText(content: string): void {
    if (!this.isConnected()) {
      logger.warn('Network', 'Cannot send text: not connected');
      return;
    }

    const message: TextMessage = {
      type: 'text',
      content,
    };

    this.send(message);
  }

  sendControl(action: 'end_turn' | 'evaluate'): void {
    if (!this.isConnected()) {
      logger.warn('Network', 'Cannot send control: not connected');
      return;
    }

    const message: ControlMessage = {
      type: 'control',
      action,
    };

    this.send(message);
  }

  private send(message: ClientMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private isConnected(): boolean {
    return this.state === ConnectionState.CONNECTED && this.ws?.readyState === WebSocket.OPEN;
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Export class for testing
export { WebSocketService };
