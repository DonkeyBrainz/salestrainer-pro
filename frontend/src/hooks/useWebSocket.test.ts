import { describe, it, expect, vi, beforeEach, afterEach, beforeAll, afterAll } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { ConnectionState } from '@/types';

// Create listener sets - these need to be hoisted so we define them here
// and use vi.hoisted() to ensure they're available before module loading
const { mockStateListeners, mockMessageListeners, mockWebsocketService } = await vi.hoisted(async () => {
  const stateListeners = new Set<(state: string) => void>();
  const messageListeners = new Set<(message: any) => void>();

  const websocketService = {
    setTokenProvider: vi.fn(),
    getState: vi.fn(() => 'DISCONNECTED'),
    onStateChange: vi.fn((listener: (state: string) => void) => {
      stateListeners.add(listener);
      return () => stateListeners.delete(listener);
    }),
    onMessage: vi.fn((listener: (message: any) => void) => {
      messageListeners.add(listener);
      return () => messageListeners.delete(listener);
    }),
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    sendAudio: vi.fn(),
    sendText: vi.fn(),
    sendControl: vi.fn(),
  };

  return {
    mockStateListeners: stateListeners,
    mockMessageListeners: messageListeners,
    mockWebsocketService: websocketService,
  };
});

// Mock dependencies
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    getValidToken: vi.fn().mockResolvedValue('test-token'),
  }),
}));

vi.mock('@/services/websocketService', () => ({
  websocketService: mockWebsocketService,
}));

// Helper to emit state changes
function emitStateChange(state: ConnectionState) {
  mockStateListeners.forEach((listener) => listener(state));
}

// Helper to emit messages
function emitMessage(message: any) {
  mockMessageListeners.forEach((listener) => listener(message));
}

// Import after mocks
import { useWebSocket } from './useWebSocket';

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStateListeners.clear();
    mockMessageListeners.clear();
    mockWebsocketService.getState.mockReturnValue(ConnectionState.DISCONNECTED);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should initialize with disconnected state', () => {
    const { result } = renderHook(() => useWebSocket());

    expect(result.current.connectionState).toBe(ConnectionState.DISCONNECTED);
    expect(result.current.isConnected).toBe(false);
    expect(result.current.isConnecting).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should set token provider on mount', () => {
    renderHook(() => useWebSocket());

    expect(mockWebsocketService.setTokenProvider).toHaveBeenCalled();
  });

  it('should connect when connect() is called', async () => {
    const { result } = renderHook(() => useWebSocket());

    await act(async () => {
      await result.current.connect();
    });

    expect(mockWebsocketService.connect).toHaveBeenCalled();
  });

  it('should disconnect when disconnect() is called', () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.disconnect();
    });

    expect(mockWebsocketService.disconnect).toHaveBeenCalled();
  });

  it('should update connection state on state change', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      emitStateChange(ConnectionState.CONNECTING);
    });

    expect(result.current.connectionState).toBe(ConnectionState.CONNECTING);
    expect(result.current.isConnecting).toBe(true);

    act(() => {
      emitStateChange(ConnectionState.CONNECTED);
    });

    expect(result.current.connectionState).toBe(ConnectionState.CONNECTED);
    expect(result.current.isConnected).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('should set error on ERROR state', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      emitStateChange(ConnectionState.ERROR);
    });

    expect(result.current.error).toBe('Connection error');
  });

  it('should add transcriptions to messages on turn_complete', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      emitMessage({ type: 'user_transcription', text: 'Hello ' });
      emitMessage({ type: 'user_transcription', text: 'world' });
      emitMessage({ type: 'turn_complete' });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].text).toBe('Hello world');
    expect(result.current.messages[0].role).toBe('user');
  });

  it('should update userTranscription with partial user_transcription chunks', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      emitMessage({ type: 'user_transcription', text: 'Hello wor' });
    });

    expect(result.current.userTranscription).toBe('Hello wor');
    expect(result.current.messages).toHaveLength(0);
  });

  it('should flush transcriptions and clear state on turn_complete', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      emitMessage({ type: 'user_transcription', text: 'Hello' });
    });

    expect(result.current.userTranscription).toBe('Hello');

    act(() => {
      emitMessage({ type: 'turn_complete' });
    });

    expect(result.current.userTranscription).toBe('');
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].text).toBe('Hello');
  });

  it('should set error on error message', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      emitMessage({
        type: 'error',
        code: 'CONNECTION_LOST',
        message: 'Connection lost',
      });
    });

    expect(result.current.error).toBe('CONNECTION_LOST: Connection lost');
  });

  it('should call onAudioReceived ref on audio message', async () => {
    const { result } = renderHook(() => useWebSocket());

    const audioHandler = vi.fn();
    result.current.onAudioReceived.current = audioHandler;

    act(() => {
      emitMessage({
        type: 'audio',
        data: 'base64-audio',
        sampleRate: 24000,
      });
    });

    expect(audioHandler).toHaveBeenCalledWith('base64-audio');
  });

  it('should send audio through service', () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.sendAudio('test-audio');
    });

    expect(mockWebsocketService.sendAudio).toHaveBeenCalledWith('test-audio');
  });

  it('should send text through service', () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.sendText('Hello');
    });

    expect(mockWebsocketService.sendText).toHaveBeenCalledWith('Hello');
  });

  it('should send control through service', () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.sendControl('end_turn');
    });

    expect(mockWebsocketService.sendControl).toHaveBeenCalledWith('end_turn');
  });

  it('should clear messages and state on disconnect', async () => {
    const { result } = renderHook(() => useWebSocket());

    // Add a message via the chunk + turn_complete flow
    act(() => {
      emitMessage({ type: 'user_transcription', text: 'Hello' });
      emitMessage({ type: 'turn_complete' });
    });

    expect(result.current.messages).toHaveLength(1);

    act(() => {
      result.current.disconnect();
    });

    expect(result.current.messages).toHaveLength(0);
    expect(result.current.currentInput).toBe('');
    expect(result.current.error).toBeNull();
  });

  it('should update completedItems and currentStage on stage_progress message', () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      emitMessage({
        type: 'stage_progress',
        current_stage: 'ASK',
        all_completed_items: ['non_business_greet', 'established_rapport'],
      });
    });

    expect(result.current.currentStage).toBe('ASK');
    expect(result.current.completedItems).toEqual(['non_business_greet', 'established_rapport']);
  });

  it('should reset completedItems and currentStage on disconnect', () => {
    const { result } = renderHook(() => useWebSocket());

    // Set some progress first
    act(() => {
      emitMessage({
        type: 'stage_progress',
        current_stage: 'SHOW',
        all_completed_items: ['non_business_greet', 'critical_questions'],
      });
    });

    expect(result.current.currentStage).toBe('SHOW');
    expect(result.current.completedItems).toHaveLength(2);

    act(() => {
      result.current.disconnect();
    });

    expect(result.current.currentStage).toBe('ENGAGE');
    expect(result.current.completedItems).toEqual([]);
  });
});
