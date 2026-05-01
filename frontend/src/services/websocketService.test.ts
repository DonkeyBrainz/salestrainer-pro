/**
 * WebSocket service tests.
 * Tests the WebSocketService class logic in isolation using a mocked WebSocket.
 */
import { describe, it, expect, vi, beforeEach, afterEach, beforeAll, afterAll } from 'vitest';
import { server } from '@/test/mocks/server';

// Define ConnectionState locally to match the actual enum
enum ConnectionState {
  DISCONNECTED = 'DISCONNECTED',
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  ERROR = 'ERROR',
}

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    mockWsInstance = this;
  }

  send = vi.fn();
  close = vi.fn();

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    const event = { type: 'open' };
    this.onopen?.(event as unknown as Event);
  }

  simulateMessage(data: unknown) {
    const event = { data: JSON.stringify(data) };
    this.onmessage?.(event as unknown as MessageEvent);
  }

  simulateClose(code: number, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    const event = { code, reason };
    this.onclose?.(event as unknown as CloseEvent);
  }

  simulateError() {
    const event = { type: 'error' };
    this.onerror?.(event as unknown as Event);
  }
}

// Store reference to mock instances
let mockWsInstance: MockWebSocket | null = null;

// Store original globals
const OriginalWebSocket = globalThis.WebSocket;

// Mock logger
vi.mock('./logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

const WS_CLOSE_CODES = {
  NORMAL: 1000,
  AUTH_FAILED: 4001,
  SESSION_LIMIT: 4002,
  RATE_LIMIT: 4003,
  INVALID_MESSAGE: 4004,
  GEMINI_FAILED: 4005,
} as const;

describe('WebSocketService', () => {
  let WebSocketService: any;
  let service: any;
  const mockTokenProvider = vi.fn();

  beforeAll(() => {
    // Stop MSW to avoid WebSocket interception
    server.close();

    // Replace WebSocket globally
    (globalThis as any).WebSocket = MockWebSocket;
  });

  afterAll(() => {
    // Restore original WebSocket
    globalThis.WebSocket = OriginalWebSocket;
    // Restart MSW
    server.listen({ onUnhandledRequest: 'error' });
  });

  beforeEach(async () => {
    vi.clearAllMocks();
    mockWsInstance = null;
    mockTokenProvider.mockResolvedValue('test-token');

    // Import fresh module for each test
    vi.resetModules();
    const module = await import('./websocketService');
    WebSocketService = module.WebSocketService;
    service = new WebSocketService();
    service.setTokenProvider(mockTokenProvider);
  });

  afterEach(() => {
    if (service) {
      service.disconnect();
    }
  });

  describe('connection', () => {
    it('should start in DISCONNECTED state', () => {
      expect(service.getState()).toBe(ConnectionState.DISCONNECTED);
    });

    it('should require token provider before connecting', async () => {
      const newService = new WebSocketService();
      await expect(newService.connect()).rejects.toThrow('Token provider not set');
    });

    it('should transition to CONNECTING when connect() is called', async () => {
      const stateHandler = vi.fn();
      service.onStateChange(stateHandler);

      const connectPromise = service.connect();

      // Need to give the promise a chance to start
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(stateHandler).toHaveBeenCalledWith(ConnectionState.CONNECTING);

      // Complete the connection
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });

      await connectPromise;
    });

    it('should transition to CONNECTED after receiving ready message', async () => {
      const connectPromise = service.connect();

      await new Promise((resolve) => setTimeout(resolve, 0));

      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });

      await connectPromise;
      expect(service.getState()).toBe(ConnectionState.CONNECTED);
    });

    it('should include token in WebSocket URL', async () => {
      const connectPromise = service.connect();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockWsInstance?.url).toContain('token=test-token');

      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });

      await connectPromise;
    });

    it('should reject connection if token provider returns null', async () => {
      mockTokenProvider.mockResolvedValue(null);

      await expect(service.connect()).rejects.toThrow('Failed to obtain authentication token');
      expect(service.getState()).toBe(ConnectionState.ERROR);
    });

    it('should not create multiple connections if already connected', async () => {
      const connectPromise = service.connect();

      await new Promise((resolve) => setTimeout(resolve, 0));
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });

      await connectPromise;

      // Try to connect again
      await service.connect();

      expect(service.getState()).toBe(ConnectionState.CONNECTED);
    });
  });

  describe('disconnection', () => {
    it('should transition to DISCONNECTED when disconnect() is called', async () => {
      const connectPromise = service.connect();
      await new Promise((resolve) => setTimeout(resolve, 0));
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });
      await connectPromise;

      service.disconnect();

      expect(service.getState()).toBe(ConnectionState.DISCONNECTED);
      expect(mockWsInstance?.close).toHaveBeenCalled();
    });

    it('should handle auth failure close code', async () => {
      const stateHandler = vi.fn();
      service.onStateChange(stateHandler);

      service.connect().catch(() => {}); // Ignore rejection
      await new Promise((resolve) => setTimeout(resolve, 0));

      mockWsInstance?.simulateClose(WS_CLOSE_CODES.AUTH_FAILED);

      expect(service.getState()).toBe(ConnectionState.ERROR);
      expect(stateHandler).toHaveBeenCalledWith(ConnectionState.ERROR);
    });

    it('should handle rate limit close code', async () => {
      const connectPromise = service.connect();
      await new Promise((resolve) => setTimeout(resolve, 0));
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });
      await connectPromise;

      mockWsInstance?.simulateClose(WS_CLOSE_CODES.RATE_LIMIT);

      expect(service.getState()).toBe(ConnectionState.ERROR);
    });
  });

  describe('message handling', () => {
    it('should notify message listeners', async () => {
      const messageHandler = vi.fn();
      service.onMessage(messageHandler);

      const connectPromise = service.connect();
      await new Promise((resolve) => setTimeout(resolve, 0));
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });
      await connectPromise;

      const testMessage = { type: 'transcription', role: 'user', text: 'hello', isFinal: true };
      mockWsInstance?.simulateMessage(testMessage);

      expect(messageHandler).toHaveBeenCalledWith(testMessage);
    });

    it('should allow unsubscribing from messages', async () => {
      const messageHandler = vi.fn();
      const unsubscribe = service.onMessage(messageHandler);

      const connectPromise = service.connect();
      await new Promise((resolve) => setTimeout(resolve, 0));
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });
      await connectPromise;

      unsubscribe();

      mockWsInstance?.simulateMessage({ type: 'transcription', role: 'user', text: 'hello', isFinal: true });

      // Only called for the ready message
      expect(messageHandler).toHaveBeenCalledTimes(1);
    });
  });

  describe('state change notifications', () => {
    it('should notify state change listeners', async () => {
      const stateHandler = vi.fn();
      service.onStateChange(stateHandler);

      const connectPromise = service.connect();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(stateHandler).toHaveBeenCalledWith(ConnectionState.CONNECTING);

      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });
      await connectPromise;

      expect(stateHandler).toHaveBeenCalledWith(ConnectionState.CONNECTED);
    });

    it('should allow unsubscribing from state changes', async () => {
      const stateHandler = vi.fn();
      const unsubscribe = service.onStateChange(stateHandler);

      unsubscribe();

      service.connect();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(stateHandler).not.toHaveBeenCalled();
    });
  });

  describe('sending messages', () => {
    beforeEach(async () => {
      const connectPromise = service.connect();
      await new Promise((resolve) => setTimeout(resolve, 0));
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });
      await connectPromise;
    });

    it('should send audio messages as binary', () => {
      // Valid base64 for "hello" in bytes
      const validBase64 = btoa('hello');
      service.sendAudio(validBase64);

      // Should send as Uint8Array (binary), not JSON
      expect(mockWsInstance?.send).toHaveBeenCalled();
      const sentData = (mockWsInstance?.send as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(sentData).toBeInstanceOf(Uint8Array);
      // Verify the decoded content matches
      const decoded = new TextDecoder().decode(sentData);
      expect(decoded).toBe('hello');
    });

    it('should send text messages', () => {
      service.sendText('Hello world');

      expect(mockWsInstance?.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'text',
          content: 'Hello world',
        })
      );
    });

    it('should send control messages', () => {
      service.sendControl('end_turn');

      expect(mockWsInstance?.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'control',
          action: 'end_turn',
        })
      );
    });

    it('should not send messages when disconnected', () => {
      service.disconnect();

      service.sendAudio('test');
      service.sendText('test');
      service.sendControl('end_turn');

      const callsAfterDisconnect = mockWsInstance?.send.mock.calls.filter(
        (call: any) => call[0]
      ).length;

      expect(callsAfterDisconnect).toBe(0);
    });
  });

  describe('reconnection', () => {
    it('should attempt reconnection on unexpected close', async () => {
      vi.useFakeTimers();

      const connectPromise = service.connect();
      await vi.advanceTimersByTimeAsync(0);
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });
      await connectPromise;

      mockWsInstance?.simulateClose(WS_CLOSE_CODES.GEMINI_FAILED);

      // State is DISCONNECTED while waiting for reconnect timeout
      expect(service.getState()).toBe(ConnectionState.DISCONNECTED);

      // After timeout fires, state becomes CONNECTING
      await vi.advanceTimersByTimeAsync(1000);
      expect(service.getState()).toBe(ConnectionState.CONNECTING);

      vi.useRealTimers();
    });

    it('should not reconnect on auth failure', async () => {
      const stateHandler = vi.fn();
      service.onStateChange(stateHandler);

      service.connect().catch(() => {}); // Ignore rejection
      await new Promise((resolve) => setTimeout(resolve, 0));

      mockWsInstance?.simulateClose(WS_CLOSE_CODES.AUTH_FAILED);

      // Should go to ERROR, not CONNECTING (reconnect)
      expect(service.getState()).toBe(ConnectionState.ERROR);
      // State should have changed to CONNECTING then ERROR
      expect(stateHandler).toHaveBeenCalledWith(ConnectionState.ERROR);
    });

    it('should not reconnect on normal close', async () => {
      const connectPromise = service.connect();
      await new Promise((resolve) => setTimeout(resolve, 0));
      mockWsInstance?.simulateOpen();
      mockWsInstance?.simulateMessage({ type: 'ready' });
      await connectPromise;

      mockWsInstance?.simulateClose(WS_CLOSE_CODES.NORMAL);

      expect(service.getState()).toBe(ConnectionState.DISCONNECTED);
    });
  });
});
